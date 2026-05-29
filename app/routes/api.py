# ============================================================
# app/routes/api.py — REST API Blueprint (v1)
# JSON endpoints consumed by frontend JS and external tools
# ============================================================
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from app import db
from app.models.attendance import Attendance, AttendanceStatus
from app.models.student import Student
from app.models.risk import RiskPrediction
from app.models.security_log import SecurityLog, EventType
from utils.decorators import role_required
from datetime import date

api_bp = Blueprint('api', __name__)


# ── Attendance endpoints ─────────────────────────────────────

@api_bp.route('/attendance/today', methods=['GET'])
@login_required
@role_required('faculty', 'admin')
def get_today_attendance():
    """Return today's attendance for a given subject."""
    subject_id = request.args.get('subject_id', type=int)
    if not subject_id:
        return jsonify({'error': 'subject_id required'}), 400

    records = (Attendance.query
               .filter_by(subject_id=subject_id, date=date.today())
               .all())
    return jsonify([r.to_dict() for r in records])


@api_bp.route('/attendance/student/<int:student_id>', methods=['GET'])
@login_required
def get_student_attendance(student_id):
    """Return all attendance records for a student (paginated)."""
    # Students can only view their own records
    if current_user.role == 'student' and current_user.student_id != student_id:
        return jsonify({'error': 'Forbidden'}), 403

    page    = request.args.get('page', 1, type=int)
    records = (Attendance.query
               .filter_by(student_id=student_id)
               .order_by(Attendance.date.desc())
               .paginate(page=page, per_page=20, error_out=False))
    return jsonify({
        'records': [r.to_dict() for r in records.items],
        'total':   records.total,
        'pages':   records.pages,
        'page':    records.page,
    })


# ── Student endpoints ────────────────────────────────────────

@api_bp.route('/students', methods=['GET'])
@login_required
@role_required('faculty', 'admin')
def list_students():
    """Return all active students (optionally filter by dept/semester)."""
    dept_id  = request.args.get('dept_id', type=int)
    semester = request.args.get('semester', type=int)

    query = Student.query.filter_by(is_active=True)
    if dept_id:
        query = query.filter_by(dept_id=dept_id)
    if semester:
        query = query.filter_by(semester=semester)

    students = query.order_by(Student.name).all()
    return jsonify([s.to_dict() for s in students])


# ── Risk prediction endpoints ────────────────────────────────

@api_bp.route('/risk/predict/<int:student_id>', methods=['POST'])
@login_required
@role_required('faculty', 'admin')
def predict_risk(student_id):
    """Trigger risk prediction for a student and save result."""
    from app.services.risk_service import RiskService
    try:
        result = RiskService.predict_for_student(student_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/risk/all', methods=['GET'])
@login_required
@role_required('faculty', 'admin')
def get_all_risk():
    """Return latest risk prediction for every student."""
    predictions = (RiskPrediction.query
                   .order_by(RiskPrediction.predicted_at.desc())
                   .all())
    return jsonify([p.to_dict() for p in predictions])


# ── Security endpoints ───────────────────────────────────────

@api_bp.route('/security/logs', methods=['GET'])
@login_required
@role_required('admin')
def get_security_logs():
    """Return recent security logs (last 100)."""
    logs = (SecurityLog.query
            .order_by(SecurityLog.timestamp.desc())
            .limit(100)
            .all())
    return jsonify([l.to_dict() for l in logs])


# ── Dashboard analytics endpoints ───────────────────────────

@api_bp.route('/analytics/attendance-summary', methods=['GET'])
@login_required
@role_required('faculty', 'admin')
def attendance_summary():
    """Return department-wide attendance stats for charts."""
    from sqlalchemy import func
    from app.models.attendance import Attendance

    result = (db.session.query(
        Attendance.status,
        func.count(Attendance.attend_id).label('count')
    ).group_by(Attendance.status).all())

    return jsonify({row.status.value: row.count for row in result})
