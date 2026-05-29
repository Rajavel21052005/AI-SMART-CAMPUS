# ============================================================
# app/services/attendance_service.py — Attendance Logic
# Handles auto-attendance, late detection, absent generation
# ============================================================
import logging
from datetime import date, datetime, timedelta
from flask import current_app

logger = logging.getLogger(__name__)


class AttendanceService:
    """
    Implements smart attendance rules:
    - Present:  arrived before class_start + LATE_THRESHOLD_MINUTES
    - Late:     arrived after threshold but before class ends
    - Absent:   no face detected throughout the class
    """

    @staticmethod
    def mark_attendance(student_id: int, subject_id: int, confidence: float):
        """
        Mark attendance for a student in a subject based on current time.
        Called by the face recognition pipeline after a confirmed match.
        Returns the Attendance record created or updated.
        """
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.timetable import Timetable, DayOfWeek
        from app import db

        today = date.today()
        now   = datetime.now().time()

        # Prevent duplicate entries for the same day
        existing = Attendance.query.filter_by(
            student_id=student_id,
            subject_id=subject_id,
            date=today,
        ).first()

        if existing:
            # Update exit time on second detection
            existing.time_out = datetime.now()
            db.session.commit()
            logger.info(f'Exit time updated for student {student_id}, subject {subject_id}')
            return existing

        # Determine status based on timetable
        status = AttendanceService._determine_status(subject_id, now, today)

        record = Attendance(
            student_id=student_id,
            subject_id=subject_id,
            date=today,
            time_in=datetime.now(),
            status=status,
            confidence_score=confidence,
        )
        db.session.add(record)
        db.session.commit()
        logger.info(f'Attendance marked: student={student_id} sub={subject_id} status={status.value}')
        return record

    @staticmethod
    def _determine_status(subject_id: int, current_time, today):
        """Determine Present / Late / Absent based on timetable."""
        from app.models.attendance import AttendanceStatus
        from app.models.timetable import Timetable, DayOfWeek

        day_name = today.strftime('%A').upper()
        try:
            day_enum = DayOfWeek[day_name]
        except KeyError:
            return AttendanceStatus.ABSENT

        slot = Timetable.query.filter_by(subject_id=subject_id, day=day_enum).first()
        if not slot:
            return AttendanceStatus.PRESENT  # No timetable — just mark present

        late_minutes = current_app.config.get('LATE_THRESHOLD_MINUTES', 10)
        threshold    = (datetime.combine(today, slot.start_time) + timedelta(minutes=late_minutes)).time()

        if current_time <= threshold:
            return AttendanceStatus.PRESENT
        return AttendanceStatus.LATE

    @staticmethod
    def generate_absents_for_class(subject_id: int, class_date: date):
        """
        After a class ends, auto-mark all students who never appeared as Absent.
        Should be called by a scheduled job (e.g. Celery/APScheduler) after each period.
        """
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.subject import Subject
        from app.models.student import Student
        from app import db

        subject  = Subject.query.get(subject_id)
        if not subject:
            return

        students = Student.query.filter_by(
            dept_id=subject.dept_id,
            semester=subject.semester,
            is_active=True,
        ).all()

        count = 0
        for s in students:
            already = Attendance.query.filter_by(
                student_id=s.student_id,
                subject_id=subject_id,
                date=class_date,
            ).first()
            if not already:
                absent = Attendance(
                    student_id=s.student_id,
                    subject_id=subject_id,
                    date=class_date,
                    status=AttendanceStatus.ABSENT,
                    is_manual=False,
                )
                db.session.add(absent)
                count += 1

        db.session.commit()
        logger.info(f'Auto-absent: {count} students marked for subject {subject_id} on {class_date}')
        return count

    @staticmethod
    def get_attendance_summary(student_id: int):
        """Return a dict with per-subject attendance stats for a student."""
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.subject import Subject
        from app.models.student import Student
        from app import db

        student  = Student.query.get(student_id)
        subjects = Subject.query.filter_by(dept_id=student.dept_id, semester=student.semester).all()

        summary = []
        for subj in subjects:
            total   = Attendance.query.filter_by(student_id=student_id, subject_id=subj.subject_id).count()
            present = Attendance.query.filter_by(student_id=student_id, subject_id=subj.subject_id).filter(
                Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
            ).count()
            pct = round((present / total) * 100, 2) if total > 0 else 0.0
            summary.append({
                'subject':  subj.to_dict(),
                'total':    total,
                'present':  present,
                'pct':      pct,
                'at_risk':  pct < current_app.config.get('MIN_ATTENDANCE_PERCENT', 75.0),
            })
        return summary
