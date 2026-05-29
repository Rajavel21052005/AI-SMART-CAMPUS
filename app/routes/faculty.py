# ============================================================
# app/routes/faculty.py — Faculty Blueprint
# ============================================================
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, send_file
from flask_login import login_required, current_user
from utils.decorators import faculty_required
from app.models.student import Student
from app.models.subject import Subject
from app.models.attendance import Attendance, AttendanceStatus
from app.models.marks import Marks
from app.models.risk import RiskPrediction, RiskLevel
from app import db
from datetime import date, datetime
import io

faculty_bp = Blueprint('faculty', __name__)


@faculty_bp.route('/dashboard')
@login_required
@faculty_required
def dashboard():
    """Faculty home dashboard — overview statistics."""
    # Subjects assigned to this faculty
    subjects = Subject.query.filter_by(faculty_id=current_user.faculty_id).all()

    # Today's attendance summary across all subjects
    today = date.today()
    today_stats = []
    for subj in subjects:
        total   = Student.query.filter_by(dept_id=subj.dept_id, semester=subj.semester, is_active=True).count()
        present = Attendance.query.filter_by(subject_id=subj.subject_id, date=today).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
        today_stats.append({'subject': subj, 'total': total, 'present': present})

    # High-risk students in faculty's department
    high_risk = (RiskPrediction.query
                 .filter_by(risk_level=RiskLevel.HIGH)
                 .order_by(RiskPrediction.predicted_at.desc())
                 .limit(10)
                 .all())

    return render_template('faculty/dashboard.html',
                           faculty=current_user,
                           subjects=subjects,
                           today_stats=today_stats,
                           high_risk=high_risk)


@faculty_bp.route('/attendance/live/<int:subject_id>')
@login_required
@faculty_required
def live_attendance(subject_id):
    """Live attendance view for a running class."""
    subject = Subject.query.get_or_404(subject_id)
    today   = date.today()
    records = (Attendance.query
               .filter_by(subject_id=subject_id, date=today)
               .all())
    students = Student.query.filter_by(
        dept_id=subject.dept_id,
        semester=subject.semester,
        is_active=True
    ).order_by(Student.name).all()
    return render_template('faculty/live_attendance.html',
                           subject=subject,
                           records=records,
                           students=students)


@faculty_bp.route('/attendance/manual', methods=['POST'])
@login_required
@faculty_required
def manual_attendance():
    """Faculty can manually override attendance status."""
    data       = request.get_json()
    attend_id  = data.get('attend_id')
    new_status = data.get('status')

    try:
        status_enum = AttendanceStatus[new_status.upper()]
    except (KeyError, AttributeError):
        return jsonify({'error': 'Invalid status'}), 400

    record = Attendance.query.get_or_404(attend_id)
    record.status    = status_enum
    record.is_manual = True
    db.session.commit()
    return jsonify({'message': 'Updated', 'attend_id': attend_id})


@faculty_bp.route('/defaulters')
@login_required
@faculty_required
def defaulters():
    """List students below minimum attendance threshold."""
    from flask import current_app
    threshold = current_app.config.get('MIN_ATTENDANCE_PERCENT', 75.0)
    subjects  = Subject.query.filter_by(faculty_id=current_user.faculty_id).all()
    defaulter_list = []

    for subj in subjects:
        students = Student.query.filter_by(
            dept_id=subj.dept_id, semester=subj.semester, is_active=True
        ).all()
        for s in students:
            pct = s.get_attendance_percentage(subject_id=subj.subject_id)
            if pct < threshold:
                defaulter_list.append({
                    'student': s, 'subject': subj,
                    'pct': pct, 'threshold': threshold
                })

    return render_template('faculty/defaulters.html', defaulters=defaulter_list, faculty=current_user)


@faculty_bp.route('/marks/update', methods=['POST'])
@login_required
@faculty_required
def update_marks():
    """Update internal marks for a student in a subject."""
    data       = request.get_json()
    student_id = data.get('student_id')
    subject_id = data.get('subject_id')

    marks = Marks.query.filter_by(student_id=student_id, subject_id=subject_id).first()
    if not marks:
        marks = Marks(student_id=student_id, subject_id=subject_id,
                      semester=data.get('semester', 1), year=data.get('year', 1))
        db.session.add(marks)

    marks.cia1       = float(data.get('cia1', 0))
    marks.cia2       = float(data.get('cia2', 0))
    marks.lab_mark   = float(data.get('lab_mark', 0))
    marks.assignment = float(data.get('assignment', 0))
    marks.compute_total()
    db.session.commit()

    return jsonify({'message': 'Marks saved', 'total': marks.total, 'gpa': marks.gpa})


@faculty_bp.route('/export/attendance/<int:subject_id>')
@login_required
@faculty_required
def export_attendance(subject_id):
    """Export attendance for a subject as Excel file."""
    from utils.excel_generator import generate_attendance_excel
    subject = Subject.query.get_or_404(subject_id)
    records = Attendance.query.filter_by(subject_id=subject_id).all()
    output  = generate_attendance_excel(subject, records)
    return send_file(
        io.BytesIO(output),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'attendance_{subject.code}.xlsx'
    )
