# ============================================================
# tests/test_attendance.py — Attendance Service Unit Tests
# ============================================================
import pytest
from datetime import date
from app import create_app, db
from app.models.department import Department
from app.models.student    import Student
from app.models.subject    import Subject
from app.models.attendance import Attendance, AttendanceStatus
from config.config         import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        dept = Department(name='Computer Science', code='CSE')
        db.session.add(dept)
        db.session.flush()

        subj = Subject(code='CS101', name='Intro to CS', dept_id=dept.dept_id, semester=1, credits=3)
        db.session.add(subj)
        db.session.flush()

        student = Student(reg_number='22CS001', name='Test Student',
                          email='student@test.com', dept_id=dept.dept_id,
                          semester=1, year=1)
        student.set_password('Pass@1234')
        db.session.add(student)
        db.session.commit()

        yield app
        db.drop_all()


def test_attendance_record_created(app):
    """Attendance record can be created and queried."""
    with app.app_context():
        s = Student.query.first()
        subj = Subject.query.first()

        record = Attendance(
            student_id=s.student_id,
            subject_id=subj.subject_id,
            date=date.today(),
            status=AttendanceStatus.PRESENT,
            confidence_score=0.95,
        )
        db.session.add(record)
        db.session.commit()

        fetched = Attendance.query.filter_by(student_id=s.student_id).first()
        assert fetched is not None
        assert fetched.status == AttendanceStatus.PRESENT
        assert fetched.confidence_score == 0.95


def test_attendance_percentage(app):
    """Student attendance percentage computation is correct."""
    with app.app_context():
        s    = Student.query.first()
        subj = Subject.query.first()

        # 3 Present, 1 Absent → 75%
        from datetime import timedelta
        for i, status in enumerate([AttendanceStatus.PRESENT]*3 + [AttendanceStatus.ABSENT]):
            rec = Attendance(
                student_id=s.student_id,
                subject_id=subj.subject_id,
                date=date.today() - timedelta(days=i),
                status=status,
            )
            db.session.add(rec)
        db.session.commit()

        pct = s.get_attendance_percentage()
        assert pct == 75.0


def test_duplicate_attendance_prevented(app):
    """Two attendance records for same student/subject/date should fail on unique constraint."""
    with app.app_context():
        s    = Student.query.first()
        subj = Subject.query.first()
        today = date.today()

        db.session.add(Attendance(student_id=s.student_id, subject_id=subj.subject_id,
                                   date=today, status=AttendanceStatus.PRESENT))
        db.session.commit()

        db.session.add(Attendance(student_id=s.student_id, subject_id=subj.subject_id,
                                   date=today, status=AttendanceStatus.LATE))
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            db.session.commit()
