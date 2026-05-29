# ============================================================
# utils/decorators.py — Role-based access decorators
# Usage: @role_required('admin')  or  @role_required('faculty', 'admin')
# ============================================================
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def role_required(*roles):
    """
    Decorator to restrict a route to specific user roles.
    Example:
        @faculty_bp.route('/dashboard')
        @login_required
        @role_required('faculty', 'admin')
        def dashboard(): ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def student_required(f):
    """Shortcut: only students can access."""
    return role_required('student')(f)


def faculty_required(f):
    """Shortcut: only faculty (and admin) can access."""
    return role_required('faculty', 'admin')(f)


def admin_required(f):
    """Shortcut: only admin can access."""
    return role_required('admin')(f)
