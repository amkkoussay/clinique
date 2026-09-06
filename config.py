"""
Clinic Management Platform - Configuration
==========================================
Configuration settings for the Flask application.
"""

import os
from datetime import timedelta

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def database_url():
    """Use the psycopg 3 driver for Replit's PostgreSQL URL."""
    value = os.environ.get('DATABASE_URL')
    if value and value.startswith('postgres://'):
        return value.replace('postgres://', 'postgresql+psycopg://', 1)
    if value and value.startswith('postgresql://'):
        return value.replace('postgresql://', 'postgresql+psycopg://', 1)
    return value


class Config:
    """Base configuration class."""
    
    # Secret key for session management and CSRF protection
    SECRET_KEY = (
        os.environ.get('SECRET_KEY')
        or os.environ.get('SESSION_SECRET')
        or 'your-super-secret-key-change-in-production'
    )
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = database_url() or \
        'sqlite:///' + os.path.join(BASE_DIR, 'clinic.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Mail configuration (for password reset and notifications)
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # AI configuration. Qwen remains supported, while OpenAI is used as the
    # managed fallback for this deployment when no Qwen key is present.
    QWEN_API_KEY = (
        os.environ.get('QWEN_API_KEY')
        or os.environ.get('DASHSCOPE_API_KEY')
        or os.environ.get('OPENAI_API_KEY')
    )
    QWEN_BASE_URL = (
        os.environ.get('QWEN_BASE_URL')
        or os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL')
        or ('https://api.openai.com/v1' if os.environ.get('OPENAI_API_KEY') else 'https://dashscope-intl.aliyuncs.com/compatible-mode/v1')
    )
    QWEN_MODEL = (
        os.environ.get('QWEN_MODEL')
        or os.environ.get('OPENAI_MODEL')
        or ('gpt-4.1-mini' if os.environ.get('OPENAI_API_KEY') else 'qwen3.8-max-0902')
    )
    AI_PROVIDER = 'openai' if os.environ.get('OPENAI_API_KEY') and not (
        os.environ.get('QWEN_API_KEY') or os.environ.get('DASHSCOPE_API_KEY')
    ) else 'qwen'
    QWEN_TIMEOUT = int(os.environ.get('QWEN_TIMEOUT') or 45)
    N8N_WEBHOOK_URL = os.environ.get('N8N_WEBHOOK_URL')
    N8N_API_KEY = os.environ.get('N8N_API_KEY')

    # Clinic configuration
    CLINIC_NAME = os.environ.get('CLINIC_NAME') or 'MediCare Clinic'
    CLINIC_ADDRESS = os.environ.get('CLINIC_ADDRESS') or '123 Healthcare Street, Medical City'
    CLINIC_PHONE = os.environ.get('CLINIC_PHONE') or '+1 (555) 123-4567'
    CLINIC_EMAIL = os.environ.get('CLINIC_EMAIL') or 'info@medicare-clinic.com'
    CLINIC_TIMEZONE = os.environ.get('CLINIC_TIMEZONE') or 'Africa/Tunis'
    
    # Pagination
    POSTS_PER_PAGE = 10
    PATIENTS_PER_PAGE = 20
    APPOINTMENTS_PER_PAGE = 15
    
    # Supported languages
    LANGUAGES = ['en', 'ar']
    BABEL_DEFAULT_LOCALE = 'en'


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    
    # Use environment variable for secret key in production
    SECRET_KEY = (
        os.environ.get('SECRET_KEY')
        or os.environ.get('SESSION_SECRET')
        or Config.SECRET_KEY
    )
    
    # Production database
    SQLALCHEMY_DATABASE_URI = database_url()


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
