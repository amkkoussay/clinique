"""
Clinic Management Platform - Authentication Routes
==================================================
Routes for user authentication, registration, and password management.
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from urllib.parse import urlparse
from datetime import datetime

from models import db, User, AuditLog
from forms import (
    LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
)

auth_bp = Blueprint('auth', __name__)


def log_action(action, entity_type=None, entity_id=None, description=None):
    """Log user action to audit log."""
    log = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        user_email=current_user.email if current_user.is_authenticated else request.form.get('email'),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:255] if request.user_agent else None
    )
    db.session.add(log)
    db.session.commit()


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'error')
                return render_template('auth/login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            log_action('login', description=f"User {user.email} logged in")
            
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('dashboard.index')
            
            flash(f'Welcome back, {user.first_name}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password.', 'error')
            log_action('login_failed', description=f"Failed login attempt for {form.email.data}")
    
    return render_template('auth/login.html', form=form, title='Sign In')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout route."""
    log_action('logout', description=f"User {current_user.email} logged out")
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = RegistrationForm()
    
    if form.validate_on_submit():
        # Check if email already exists
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash('Email address already registered.', 'error')
            return render_template('auth/register.html', form=form)
        
        # Create new user
        user = User(
            email=form.email.data.lower(),
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            phone=form.phone.data,
            role=form.role.data,
            specialization=form.specialization.data if form.role.data == 'doctor' else None,
            license_number=form.license_number.data if form.role.data == 'doctor' else None
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        log_action('register', 'User', user.id, f"New user registered: {user.email}")
        
        flash('Registration successful! Please sign in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html', form=form, title='Sign Up')


@auth_bp.route('/reset-password-request', methods=['GET', 'POST'])
def reset_password_request():
    """Password reset request route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    form = ResetPasswordRequestForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        
        if user:
            # In a production environment, send email with reset link
            # For now, we'll just show a message
            log_action('password_reset_requested', 'User', user.id, 
                      f"Password reset requested for {user.email}")
            flash('Check your email for instructions to reset your password.', 'info')
        else:
            # Don't reveal if email exists
            flash('Check your email for instructions to reset your password.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password_request.html', form=form, title='Reset Password')


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset route."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    
    # In production, verify token validity
    # For now, we'll just show the form
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        # In production, get user from token
        # For now, this is a placeholder
        flash('Your password has been reset.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', form=form, title='Reset Password')


@auth_bp.route('/profile')
@login_required
def profile():
    """User profile route."""
    return render_template('auth/profile.html', title='My Profile')


@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile route."""
    from forms import RegistrationForm
    
    # Create a custom form without password fields
    class EditProfileForm(RegistrationForm):
        password = None
        password2 = None
        role = None
    
    form = EditProfileForm(obj=current_user)
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.phone = form.phone.data
        
        if current_user.is_doctor():
            current_user.specialization = form.specialization.data
            current_user.license_number = form.license_number.data
        
        db.session.commit()
        
        log_action('update', 'User', current_user.id, "Profile updated")
        
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html', form=form, title='Edit Profile')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change password route."""
    from wtforms import Form, PasswordField, SubmitField
    from wtforms.validators import DataRequired, EqualTo, Length
    
    class ChangePasswordForm(Form):
        current_password = PasswordField('Current Password', validators=[DataRequired()])
        new_password = PasswordField('New Password', validators=[
            DataRequired(),
            Length(min=8, message='Password must be at least 8 characters')
        ])
        confirm_password = PasswordField('Confirm New Password', validators=[
            DataRequired(),
            EqualTo('new_password', message='Passwords must match')
        ])
        submit = SubmitField('Change Password')
    
    form = ChangePasswordForm()
    
    if request.method == 'POST' and form.validate():
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'error')
            return render_template('auth/change_password.html', form=form)
        
        current_user.set_password(form.new_password.data)
        db.session.commit()
        
        log_action('password_changed', 'User', current_user.id, "Password changed")
        
        flash('Password changed successfully.', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/change_password.html', form=form, title='Change Password')


@auth_bp.route('/users')
@login_required
def list_users():
    """List all users (admin only)."""
    if not current_user.is_admin():
        flash('Access denied. Administrator privileges required.', 'error')
        return redirect(url_for('dashboard.index'))
    
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(
        page=page, 
        per_page=10, 
        error_out=False
    )
    
    return render_template('auth/users.html', users=users, title='Manage Users')


@auth_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)."""
    if not current_user.is_admin():
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard.index'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('auth.list_users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    log_action('update', 'User', user.id, f"User {status}")
    
    flash(f'User {status} successfully.', 'success')
    return redirect(url_for('auth.list_users'))
