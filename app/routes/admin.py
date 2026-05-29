# ============================================================
# app/routes/admin.py — Admin Blueprint
# ============================================================
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required
from utils.decorators import admin_required
from app import db
from app.models.student import Student
from app.models.faculty import Faculty
from app.models.department import Department
from app.models.subject import Subject
from app.models.security_log import SecurityLog
from utils.helpers import save_uploaded_photo

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin system-wide overview."""
    stats = {
        'total_students': Student.query.filter_by(is_active=True).count(),
        'total_faculty':  Faculty.query.filter_by(is_active=True).count(),
        'total_subjects': Subject.query.count(),
        'total_depts':    Department.query.count(),
        'security_alerts': SecurityLog.query.filter_by(resolved=False).count(),
    }
    recent_security = (SecurityLog.query
                       .order_by(SecurityLog.timestamp.desc())
                       .limit(10).all())
    return render_template('admin/dashboard.html',
                           stats=stats,
                           recent_security=recent_security)


# ── Student CRUD ─────────────────────────────────────────────

@admin_bp.route('/students')
@login_required
@admin_required
def students():
    page     = request.args.get('page', 1, type=int)
    search   = request.args.get('q', '')
    query    = Student.query.filter_by(is_active=True)
    if search:
        query = query.filter(
            db.or_(Student.name.ilike(f'%{search}%'),
                   Student.reg_number.ilike(f'%{search}%'))
        )
    students = query.order_by(Student.name).paginate(page=page, per_page=25)
    return render_template('admin/students.html', students=students, search=search)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_student():
    departments = Department.query.all()
    if request.method == 'POST':
        try:
            student = Student(
                reg_number=request.form['reg_number'],
                name=request.form['name'],
                email=request.form['email'],
                phone=request.form.get('phone'),
                dept_id=int(request.form['dept_id']),
                semester=int(request.form['semester']),
                year=int(request.form['year']),
            )
            student.set_password(request.form['password'])

            # Handle photo upload
            photo = request.files.get('photo')
            if photo:
                path = save_uploaded_photo(photo, subfolder='students')
                student.photo_path = path

            db.session.add(student)
            db.session.commit()
            flash(f'Student {student.name} added successfully.', 'success')
            return redirect(url_for('admin.students'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding student: {str(e)}', 'danger')

    return render_template('admin/add_student.html', departments=departments)


@admin_bp.route('/students/delete/<int:student_id>', methods=['POST'])
@login_required
@admin_required
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    student.is_active = False  # Soft delete
    db.session.commit()
    flash(f'Student {student.name} deactivated.', 'info')
    return redirect(url_for('admin.students'))


# ── Face model training ──────────────────────────────────────

@admin_bp.route('/train-model', methods=['GET', 'POST'])
@login_required
@admin_required
def train_model():
    """Trigger face recognition model retraining."""
    if request.method == 'POST':
        from app.services.face_service import FaceService
        try:
            result = FaceService.train_encodings()
            flash(f'Model trained successfully. {result["count"]} encodings generated.', 'success')
        except Exception as e:
            flash(f'Training failed: {str(e)}', 'danger')
    return render_template('admin/train_model.html')


# ── Department management ────────────────────────────────────

@admin_bp.route('/departments', methods=['GET', 'POST'])
@login_required
@admin_required
def departments():
    if request.method == 'POST':
        dept = Department(
            name=request.form['name'],
            code=request.form['code'].upper(),
            hod_name=request.form.get('hod_name')
        )
        db.session.add(dept)
        db.session.commit()
        flash('Department added.', 'success')
    depts = Department.query.all()
    return render_template('admin/departments.html', departments=depts)


# ── Security monitoring ──────────────────────────────────────

@admin_bp.route('/security')
@login_required
@admin_required
def security():
    """View all security events."""
    page = request.args.get('page', 1, type=int)
    logs = (SecurityLog.query
            .order_by(SecurityLog.timestamp.desc())
            .paginate(page=page, per_page=20))
    return render_template('admin/security.html', logs=logs)


@admin_bp.route('/security/resolve/<int:log_id>', methods=['POST'])
@login_required
@admin_required
def resolve_security(log_id):
    log = SecurityLog.query.get_or_404(log_id)
    log.resolved = True
    db.session.commit()
    return jsonify({'message': 'Resolved'})
