# ============================================================
# app/models/assignment.py — Assignment Tracking Model
# ============================================================
import enum
from app import db
from datetime import datetime


class SubmissionStatus(enum.Enum):
    PENDING   = 'Pending'
    SUBMITTED = 'Submitted'
    LATE      = 'Late'
    MISSING   = 'Missing'


class Assignment(db.Model):
    __tablename__ = 'assignments'

    assign_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    subject_id  = db.Column(db.Integer, db.ForeignKey('subjects.subject_id'), nullable=False)
    student_id  = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    due_date    = db.Column(db.DateTime, nullable=False)
    submitted_at = db.Column(db.DateTime)
    status      = db.Column(db.Enum(SubmissionStatus), default=SubmissionStatus.PENDING)
    marks_obtained = db.Column(db.Float, default=0.0)
    max_marks   = db.Column(db.Float, default=10.0)
    file_path   = db.Column(db.String(255))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'assign_id':    self.assign_id,
            'title':        self.title,
            'subject_id':   self.subject_id,
            'student_id':   self.student_id,
            'due_date':     self.due_date.isoformat(),
            'status':       self.status.value,
            'marks_obtained': self.marks_obtained,
        }
