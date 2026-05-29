# ============================================================
# app/routes/student.py — Student Blueprint
# ============================================================
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from utils.decorators import student_required
from app.models.attendance import Attendance, AttendanceStatus
from app.models.marks import Marks
from app.models.assignment import Assignment, SubmissionStatus
from app.models.timetable import Timetable, DayOfWeek
from app.models.notification import Notification
from app.models.risk import RiskPrediction
from datetime import date

student_bp = Blueprint('student', __name__)


@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = current_user
    today   = date.today()

    # Overall attendance percentage
    attend_pct = student.get_attendance_percentage()

    # Subject-wise attendance
    from app import db
    from app.models.subject import Subject
    from app.models.attendance import Attendance
    from sqlalchemy import func

    subj_stats = []
    subjects = Subject.query.filter_by(dept_id=student.dept_id, semester=student.semester).all()
    for subj in subjects:
        total   = Attendance.query.filter_by(student_id=student.student_id, subject_id=subj.subject_id).count()
        present = Attendance.query.filter_by(student_id=student.student_id, subject_id=subj.subject_id).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
        pct = round((present / total) * 100, 1) if total > 0 else 0
        subj_stats.append({'subject': subj, 'total': total, 'present': present, 'pct': pct})

    # Latest risk prediction
    risk = (RiskPrediction.query
            .filter_by(student_id=student.student_id)
            .order_by(RiskPrediction.predicted_at.desc())
            .first())

    # Recent marks
    marks = Marks.query.filter_by(
        student_id=student.student_id, semester=student.semester
    ).all()

    # Pending assignments
    pending_assignments = Assignment.query.filter_by(
        student_id=student.student_id, status=SubmissionStatus.PENDING
    ).order_by(Assignment.due_date).limit(5).all()

    # Unread notifications
    notifications = Notification.query.filter_by(
        student_id=student.student_id, is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()

    # Today's timetable
    day_name = today.strftime('%A')  # e.g. "Monday"
    try:
        day_enum = DayOfWeek[day_name.upper()]
        timetable_today = Timetable.query.filter_by(
            dept_id=student.dept_id,
            semester=student.semester,
            day=day_enum
        ).order_by(Timetable.period_number).all()
    except KeyError:
        timetable_today = []

    return render_template(
        'student/dashboard.html',
        student=student,
        attend_pct=attend_pct,
        subj_stats=subj_stats,
        risk=risk,
        marks=marks,
        pending_assignments=pending_assignments,
        notifications=notifications,
        timetable_today=timetable_today,
    )


@student_bp.route('/attendance')
@login_required
@student_required
def attendance():
    """Full attendance history page."""
    records = (Attendance.query
               .filter_by(student_id=current_user.student_id)
               .order_by(Attendance.date.desc())
               .all())
    return render_template('student/attendance.html', records=records, student=current_user)


@student_bp.route('/marks')
@login_required
@student_required
def marks():
    """All marks for the student."""
    all_marks = Marks.query.filter_by(student_id=current_user.student_id).all()
    return render_template('student/marks.html', marks=all_marks, student=current_user)


@student_bp.route('/timetable')
@login_required
@student_required
def timetable():
    """Weekly timetable for the student's dept/semester."""
    days = list(DayOfWeek)
    tt   = {}
    for day in days:
        tt[day.value] = (Timetable.query
                         .filter_by(dept_id=current_user.dept_id,
                                    semester=current_user.semester,
                                    day=day)
                         .order_by(Timetable.period_number)
                         .all())
    return render_template('student/timetable.html', timetable=tt, days=days, student=current_user)


@student_bp.route('/notifications/mark-read/<int:notif_id>')
@login_required
@student_required
def mark_notification_read(notif_id):
    from app import db
    notif = Notification.query.filter_by(notif_id=notif_id, student_id=current_user.student_id).first_or_404()
    notif.is_read = True
    db.session.commit()
    return redirect(url_for('student.dashboard'))
