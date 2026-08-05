"""
Clinic Management Platform - Main Routes
========================================
Routes for the landing page and general pages.
"""

from flask import Blueprint, render_template, request, session, make_response
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Landing page route."""
    # If user is logged in, redirect to dashboard
    from flask_login import current_user
    if current_user.is_authenticated:
        return render_template('dashboard/index.html')
    
    return render_template('main/index.html', title='Welcome')


@main_bp.route('/about')
def about():
    """About page route."""
    return render_template('main/about.html', title='About Us')


@main_bp.route('/services')
def services():
    """Services page route."""
    return render_template('main/services.html', title='Our Services')


@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact page route."""
    from flask import flash
    from wtforms import Form, StringField, TextAreaField, EmailField, SubmitField
    from wtforms.validators import DataRequired, Email
    
    class ContactForm(Form):
        name = StringField('Name', validators=[DataRequired()])
        email = EmailField('Email', validators=[DataRequired(), Email()])
        subject = StringField('Subject', validators=[DataRequired()])
        message = TextAreaField('Message', validators=[DataRequired()])
        submit = SubmitField('Send Message')
    
    form = ContactForm(request.form)
    
    if request.method == 'POST' and form.validate():
        # In production, send email
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return render_template('main/contact.html', title='Contact Us', form=form, sent=True)
    
    return render_template('main/contact.html', title='Contact Us', form=form)


@main_bp.route('/set-language/<lang>')
def set_language(lang):
    """Set language preference."""
    session['language'] = lang
    return render_template('main/set_language.html', lang=lang)


@main_bp.route('/set-theme/<theme>')
def set_theme(theme):
    """Set theme preference."""
    session['theme'] = theme
    response = make_response('Theme set')
    response.set_cookie('theme', theme, max_age=365*24*60*60)  # 1 year
    return response


@main_bp.route('/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}
