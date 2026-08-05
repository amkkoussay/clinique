"""
Clinic Management Platform - Access Control Decorators
=======================================================
Simple role-based access control decorators for Flask routes.
"""

from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """
    Restrict a route to users whose role is in `roles`.

    Usage:
        @role_required('admin')
        def some_view():
            ...

        @role_required('doctor', 'admin')
        def some_other_view():
            ...

    Must be used together with (and placed below) @login_required,
    since it assumes current_user is already authenticated.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))

            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('dashboard.index'))

            return view_func(*args, **kwargs)
        return wrapped_view
    return decorator
