# ============================================================
# app/models/attendance.py — Attendance Model
# ============================================================
import enum
from app import db
from datetime import datetime


class AttendanceStatus(enum.Enum):
    PRESENT = 'Present'
    LATE    = 'Late'
    ABSENT  = 'Absent'


class Attendance(db.Model):
    __tablename__ = 'attendance'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'date', name='uq_student_subject_date'),
        db.Index('ix_attendance_date', 'date'),
        db.Index('ix_attendance_student', 'student_id'),
    )

    attend_id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id       = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    subject_id       = db.Column(db.Integer, db.ForeignKey('subjects.subject_id'), nullable=False)
    date             = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    time_in          = db.Column(db.DateTime)
    time_out         = db.Column(db.DateTime)
    status           = db.Column(db.Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.ABSENT)
    confidence_score = db.Column(db.Float)          # Face recognition confidence (0–1)
    is_manual        = db.Column(db.Boolean, default=False)  # True = faculty-corrected
    notes            = db.Column(db.String(255))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Attendance S:{self.student_id} Sub:{self.subject_id} {self.date} {self.status.value}>'

    def to_dict(self):
        return {
            'attend_id':        self.attend_id,
            'student_id':       self.student_id,
            'subject_id':       self.subject_id,
            'date':             self.date.isoformat(),
            'time_in':          self.time_in.isoformat() if self.time_in else None,
            'status':           self.status.value,
            'confidence_score': self.confidence_score,
            'is_manual':        self.is_manual,
        }
