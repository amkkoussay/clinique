"""
Clinic Management Platform - Main Application
=============================================
Flask application initialization and configuration.
"""

import os
import logging

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(dotenv_path=None, *args, **kwargs):
        """Fallback loader for environments where python-dotenv is not installed."""
        if not dotenv_path or not os.path.isfile(dotenv_path):
            return False
        loaded = False
        with open(dotenv_path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
                    loaded = True
        return loaded
from datetime import datetime
from flask import Flask, request, session, g
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

# Load local environment variables before configuration is read.
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Initialize extensions
from models import db

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask extensions
login_manager = LoginManager()
csrf = CSRFProtect()



def ensure_appointment_booking_key_column():
    """Small SQLite migration for the new appointment booking key."""
    from sqlalchemy import inspect, text
    engine = db.engine
    inspector = inspect(engine)
    if 'appointments' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('appointments')}
    if 'booking_key' in columns:
        return
    if engine.dialect.name == 'sqlite':
        with engine.begin() as conn:
            conn.execute(text('ALTER TABLE appointments ADD COLUMN booking_key VARCHAR(120)'))
            conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_appointments_booking_key ON appointments (booking_key)'))
    else:
        logger.warning('Existing database needs a migration for appointments.booking_key. Run your normal migration tool.')

def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app instances.
    
    Args:
        config_name: Configuration environment name (development, production, testing)
    
    Returns:
        Configured Flask application instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config.get(config_name, config['default']))
    
    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    register_blueprints(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register before/after request handlers
    register_request_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        ensure_appointment_booking_key_column()
        logger.info("Database tables created successfully")
    
    return app


def register_blueprints(app):
    """Register Flask blueprints."""
    # Import and register blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.dashboard import dashboard_bp
    from routes.patients import patients_bp
    from routes.appointments import appointments_bp
    from routes.medical import medical_bp
    from routes.billing import billing_bp
    from routes.chatbot import chatbot_bp
    from routes.api import api_bp
    from routes.reports import reports_bp
    from routes.fhir import fhir_bp
    from routes.integration import integration_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')
    app.register_blueprint(patients_bp, url_prefix='/patients')
    app.register_blueprint(appointments_bp, url_prefix='/appointments')
    app.register_blueprint(medical_bp, url_prefix='/medical')
    app.register_blueprint(billing_bp, url_prefix='/billing')
    app.register_blueprint(chatbot_bp, url_prefix='/chatbot')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(fhir_bp)
    app.register_blueprint(integration_bp, url_prefix='/api/integration')
    csrf.exempt(integration_bp)
    
    logger.info("Blueprints registered successfully")


def register_template_filters(app):
    """Register custom Jinja2 template filters."""
    
    @app.template_filter('format_date')
    def format_date(value, format='%B %d, %Y'):
        """Format a date object."""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return value
        return value.strftime(format)
    
    @app.template_filter('format_datetime')
    def format_datetime(value, format='%B %d, %Y %I:%M %p'):
        """Format a datetime object."""
        if value is None:
            return ''
        return value.strftime(format)
    
    @app.template_filter('format_time')
    def format_time(value, format='%I:%M %p'):
        """Format a time object."""
        if value is None:
            return ''
        if isinstance(value, str):
            return value
        return value.strftime(format)
    
    @app.template_filter('format_currency')
    def format_currency(value):
        """Format a number as currency."""
        if value is None:
            return '$0.00'
        return '${:,.2f}'.format(float(value))
    
    @app.template_filter('format_phone')
    def format_phone(value):
        """Format a phone number."""
        if not value:
            return ''
        # Simple US phone formatting
        phone = ''.join(filter(str.isdigit, str(value)))
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        return value
    
    @app.template_filter('truncate_text')
    def truncate_text(value, length=100):
        """Truncate text to specified length."""
        if not value:
            return ''
        if len(value) > length:
            return value[:length].rstrip() + '...'
        return value
    
    @app.template_filter('status_badge')
    def status_badge(value):
        """Return badge class for status."""
        status_classes = {
            'active': 'success',
            'inactive': 'secondary',
            'pending': 'warning',
            'completed': 'success',
            'cancelled': 'danger',
            'scheduled': 'primary',
            'confirmed': 'info',
            'in_progress': 'warning',
            'no_show': 'dark',
            'paid': 'success',
            'partial': 'warning',
            'overdue': 'danger',
            'low': 'success',
            'medium': 'info',
            'high': 'warning',
            'urgent': 'danger'
        }
        return status_classes.get(value.lower(), 'secondary')
    
    logger.info("Template filters registered successfully")


def register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(400)
    def bad_request_error(error):
        from flask import render_template
        logger.warning(f"Bad request: {error}")
        return render_template('errors/400.html'), 400
    
    @app.errorhandler(403)
    def forbidden_error(error):
        from flask import render_template
        logger.warning(f"Forbidden access: {error}")
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import render_template
        logger.warning(f"Page not found: {error}")
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        from flask import render_template
        logger.error(f"Internal server error: {error}")
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    logger.info("Error handlers registered successfully")


def register_request_handlers(app):
    """Register before and after request handlers."""
    
    @app.before_request
    def before_request():
        """Execute before each request."""
        # Set request start time for performance monitoring
        g.start_time = datetime.utcnow()
        
        # Set language from session or accept header
        if 'language' not in session:
            session['language'] = request.accept_languages.best_match(
                app.config['LANGUAGES']
            ) or 'en'
        
        # Set theme from session or cookie
        if 'theme' not in session:
            session['theme'] = request.cookies.get('theme', 'light')
    
    @app.after_request
    def after_request(response):
        """Execute after each request."""
        # Log request duration
        if hasattr(g, 'start_time'):
            duration = (datetime.utcnow() - g.start_time).total_seconds()
            logger.debug(f"Request to {request.path} took {duration:.3f}s")
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        return response
    
    logger.info("Request handlers registered successfully")


# User loader callback for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from models import User
    return User.query.get(int(user_id))


# Create the application instance
app = create_app()


# Shell context processor
@app.shell_context_processor
def make_shell_context():
    """Make database and models available in shell."""
    from models import (
        User, Patient, Appointment, MedicalRecord, Prescription,
        PrescriptionItem, LabTest, VitalSigns, PatientDocument,
        Invoice, InvoiceItem, Payment, Service, AuditLog,
        ChatbotConversation, Medicine, Notification, Task
    )
    return {
        'db': db,
        'User': User,
        'Patient': Patient,
        'Appointment': Appointment,
        'MedicalRecord': MedicalRecord,
        'Prescription': Prescription,
        'PrescriptionItem': PrescriptionItem,
        'LabTest': LabTest,
        'VitalSigns': VitalSigns,
        'PatientDocument': PatientDocument,
        'Invoice': Invoice,
        'InvoiceItem': InvoiceItem,
        'Payment': Payment,
        'Service': Service,
        'AuditLog': AuditLog,
        'ChatbotConversation': ChatbotConversation,
        'Medicine': Medicine,
        'Notification': Notification,
        'Task': Task
    }


# CLI commands
@app.cli.command('init-db')
def init_db():
    """Initialize the database."""
    db.create_all()
    print("Database initialized successfully!")


@app.cli.command('create-admin')
def create_admin():
    """Create admin user."""
    import click
    from models import User
    
    email = click.prompt('Email')
    first_name = click.prompt('First Name')
    last_name = click.prompt('Last Name')
    password = click.prompt('Password', hide_input=True, confirmation_prompt=True)
    
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role='admin'
    )
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    print(f"Admin user {email} created successfully!")


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
