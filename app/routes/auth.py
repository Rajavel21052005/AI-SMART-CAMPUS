# ============================================================
# app/routes/auth.py — Authentication Blueprint
# Handles login, logout, and role-based redirects
# ============================================================
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models.student import Student
from app.models.faculty import Faculty, Admin

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Unified login page for Student / Faculty / Admin."""
    if current_user.is_authenticated:
        return _redirect_by_role(current_user.role)

    if request.method == 'POST':
        role     = request.form.get('role', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        remember = bool(request.form.get('remember'))

        user = _find_user(role, username)

        if user is None or not user.check_password(password):
            flash('Invalid credentials. Please try again.', 'danger')
            return render_template('auth/login.html', role=role, username=username)

        if not user.is_active:
            flash('Your account has been deactivated. Contact admin.', 'warning')
            return render_template('auth/login.html')

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        # Redirect to the page the user originally wanted, or role dashboard
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return _redirect_by_role(user.role)

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log the current user out."""
    flash('You have been logged out.', 'info')
    logout_user()
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Allow logged-in users to change their password."""
    if request.method == 'POST':
        current_pw  = request.form.get('current_password', '')
        new_pw      = request.form.get('new_password', '')
        confirm_pw  = request.form.get('confirm_password', '')

        if not current_user.check_password(current_pw):
            flash('Current password is incorrect.', 'danger')
        elif new_pw != confirm_pw:
            flash('New passwords do not match.', 'danger')
        elif len(new_pw) < 8:
            flash('New password must be at least 8 characters.', 'danger')
        else:
            current_user.set_password(new_pw)
            db.session.commit()
            flash('Password updated successfully.', 'success')
            return _redirect_by_role(current_user.role)

    return render_template('auth/change_password.html')


# ── Helpers ─────────────────────────────────────────────────

def _find_user(role, identifier):
    """Look up user from the correct model by role."""
    if role == 'student':
        # Students can log in with reg_number or email
        return (Student.query.filter_by(reg_number=identifier).first()
                or Student.query.filter_by(email=identifier).first())
    elif role == 'faculty':
        return (Faculty.query.filter_by(employee_id=identifier).first()
                or Faculty.query.filter_by(email=identifier).first())
    elif role == 'admin':
        return (Admin.query.filter_by(username=identifier).first()
                or Admin.query.filter_by(email=identifier).first())
    return None


def _redirect_by_role(role):
    """Redirect user to their own dashboard after login."""
    destinations = {
        'student': 'student.dashboard',
        'faculty': 'faculty.dashboard',
        'admin':   'admin.dashboard',
    }
    return redirect(url_for(destinations.get(role, 'auth.login')))
