# ============================================================
# app/services/report_service.py — Unified Report Service
# Delegates to pdf_generator / excel_generator
# ============================================================
import io
import logging
from flask import send_file

logger = logging.getLogger(__name__)


class ReportService:

    @staticmethod
    def attendance_pdf(subject_id: int) -> bytes:
        from app.models.subject    import Subject
        from app.models.attendance import Attendance
        from utils.pdf_generator   import generate_attendance_pdf
        subject = Subject.query.get_or_404(subject_id)
        records = Attendance.query.filter_by(subject_id=subject_id).order_by('date').all()
        return generate_attendance_pdf(subject, records)

    @staticmethod
    def attendance_excel(subject_id: int) -> bytes:
        from app.models.subject      import Subject
        from app.models.attendance   import Attendance
        from utils.excel_generator   import generate_attendance_excel
        subject = Subject.query.get_or_404(subject_id)
        records = Attendance.query.filter_by(subject_id=subject_id).order_by('date').all()
        return generate_attendance_excel(subject, records)

    @staticmethod
    def risk_report_pdf() -> bytes:
        from app.models.risk       import RiskPrediction
        from utils.pdf_generator   import generate_risk_report_pdf
        predictions = RiskPrediction.query.order_by(RiskPrediction.predicted_at.desc()).all()
        return generate_risk_report_pdf(predictions)

    @staticmethod
    def student_list_excel(dept_id: int = None) -> bytes:
        from app.models.student      import Student
        from app.models.department   import Department
        from utils.excel_generator   import generate_student_report_excel
        query = Student.query.filter_by(is_active=True)
        if dept_id:
            query = query.filter_by(dept_id=dept_id)
        students  = query.order_by(Student.name).all()
        dept_name = Department.query.get(dept_id).name if dept_id else 'All Departments'
        return generate_student_report_excel(students, dept_name)
