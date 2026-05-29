# ============================================================
# app/routes/analytics.py — Analytics & Reports Blueprint
# Charts, PDF/Excel exports, system-wide statistics
# ============================================================
import io
from flask import (Blueprint, render_template, request, send_file,
                   jsonify, current_app)
from flask_login import login_required
from utils.decorators import faculty_required, admin_required
from app import db
from app.models.attendance  import Attendance, AttendanceStatus
from app.models.student     import Student
from app.models.subject     import Subject
from app.models.marks       import Marks
from app.models.risk        import RiskPrediction, RiskLevel
from app.models.department  import Department
from sqlalchemy              import func
from datetime               import date, timedelta

analytics_bp = Blueprint('analytics', __name__)


# ── Analytics dashboard ───────────────────────────────────────

@analytics_bp.route('/dashboard')
@login_required
@faculty_required
def dashboard():
    """Analytics overview page with charts."""
    # Attendance trend: last 14 days
    today  = date.today()
    trend  = []
    for i in range(13, -1, -1):
        d     = today - timedelta(days=i)
        total = Attendance.query.filter_by(date=d).count()
        pres  = Attendance.query.filter_by(date=d).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
        trend.append({'date': d.strftime('%d %b'), 'total': total, 'present': pres,
                      'pct': round(pres / total * 100, 1) if total else 0})

    # Risk distribution
    risk_counts = {
        'Safe':     RiskPrediction.query.filter_by(risk_level=RiskLevel.SAFE).count(),
        'Moderate': RiskPrediction.query.filter_by(risk_level=RiskLevel.MODERATE).count(),
        'High':     RiskPrediction.query.filter_by(risk_level=RiskLevel.HIGH).count(),
    }

    # Department attendance averages
    dept_stats = []
    for dept in Department.query.all():
        students = Student.query.filter_by(dept_id=dept.dept_id, is_active=True).all()
        if not students:
            continue
        avg_pct = round(
            sum(s.get_attendance_percentage() for s in students) / len(students), 1
        )
        dept_stats.append({'name': dept.code, 'avg_pct': avg_pct, 'count': len(students)})

    # Top defaulters (bottom 5 by attendance)
    all_students = Student.query.filter_by(is_active=True).all()
    defaulters   = sorted(
        [{'student': s, 'pct': s.get_attendance_percentage()} for s in all_students],
        key=lambda x: x['pct']
    )[:5]

    # Subject-wise attendance
    subj_stats = []
    for subj in Subject.query.all():
        total = Attendance.query.filter_by(subject_id=subj.subject_id).count()
        pres  = Attendance.query.filter_by(subject_id=subj.subject_id).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
        subj_stats.append({
            'name': subj.code,
            'pct':  round(pres / total * 100, 1) if total else 0
        })

    return render_template('analytics/dashboard.html',
                           trend=trend,
                           risk_counts=risk_counts,
                           dept_stats=dept_stats,
                           defaulters=defaulters,
                           subj_stats=subj_stats)


# ── API endpoints for Chart.js ────────────────────────────────

@analytics_bp.route('/api/trend')
@login_required
@faculty_required
def api_trend():
    """14-day attendance trend as JSON for charts."""
    today = date.today()
    data  = []
    for i in range(13, -1, -1):
        d     = today - timedelta(days=i)
        total = Attendance.query.filter_by(date=d).count()
        pres  = Attendance.query.filter_by(date=d).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
        data.append({'date': d.strftime('%d %b'),
                     'present': pres,
                     'absent':  total - pres,
                     'pct':     round(pres / total * 100, 1) if total else 0})
    return jsonify(data)


@analytics_bp.route('/api/risk-distribution')
@login_required
@faculty_required
def api_risk():
    return jsonify({
        'Safe':     RiskPrediction.query.filter_by(risk_level=RiskLevel.SAFE).count(),
        'Moderate': RiskPrediction.query.filter_by(risk_level=RiskLevel.MODERATE).count(),
        'High':     RiskPrediction.query.filter_by(risk_level=RiskLevel.HIGH).count(),
    })


# ── Report exports ────────────────────────────────────────────

@analytics_bp.route('/export/attendance-pdf/<int:subject_id>')
@login_required
@faculty_required
def export_attendance_pdf(subject_id):
    from app.services.report_service import ReportService
    pdf_bytes = ReportService.attendance_pdf(subject_id)
    subj      = Subject.query.get_or_404(subject_id)
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'attendance_{subj.code}.pdf'
    )


@analytics_bp.route('/export/risk-report-pdf')
@login_required
@admin_required
def export_risk_pdf():
    from app.services.report_service import ReportService
    pdf_bytes = ReportService.risk_report_pdf()
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='risk_report.pdf'
    )


@analytics_bp.route('/export/students-excel')
@login_required
@admin_required
def export_students_excel():
    from app.services.report_service import ReportService
    dept_id   = request.args.get('dept_id', type=int)
    xlsx_data = ReportService.student_list_excel(dept_id)
    return send_file(
        io.BytesIO(xlsx_data),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='students_report.xlsx'
    )
