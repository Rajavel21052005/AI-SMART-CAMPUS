# ============================================================
# app/models/__init__.py — Import all models so SQLAlchemy
# can discover them during db.create_all()
# ============================================================
from app.models.department   import Department
from app.models.student      import Student
from app.models.faculty      import Faculty, Admin
from app.models.subject      import Subject
from app.models.attendance   import Attendance, AttendanceStatus
from app.models.marks        import Marks
from app.models.assignment   import Assignment, SubmissionStatus
from app.models.timetable    import Timetable, DayOfWeek
from app.models.face_encoding import FaceEncoding
from app.models.risk         import RiskPrediction, RiskLevel
from app.models.security_log import SecurityLog, EventType
from app.models.notification import Notification, NotificationType

__all__ = [
    'Department', 'Student', 'Faculty', 'Admin',
    'Subject', 'Attendance', 'AttendanceStatus',
    'Marks', 'Assignment', 'SubmissionStatus',
    'Timetable', 'DayOfWeek', 'FaceEncoding',
    'RiskPrediction', 'RiskLevel', 'SecurityLog',
    'EventType', 'Notification', 'NotificationType',
]
