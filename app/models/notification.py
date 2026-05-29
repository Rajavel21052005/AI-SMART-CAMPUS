# ============================================================
# app/models/notification.py — Notification / Alert Model
# ============================================================
import enum
from app import db
from datetime import datetime


class NotificationType(enum.Enum):
    LOW_ATTENDANCE = 'low_attendance'
    HIGH_RISK      = 'high_risk'
    ASSIGNMENT_DUE = 'assignment_due'
    GENERAL        = 'general'


class Notification(db.Model):
    __tablename__ = 'notifications'

    notif_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    title      = db.Column(db.String(200), nullable=False)
    message    = db.Column(db.Text, nullable=False)
    notif_type = db.Column(db.Enum(NotificationType), default=NotificationType.GENERAL)
    is_read    = db.Column(db.Boolean, default=False)
    email_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'notif_id':   self.notif_id,
            'title':      self.title,
            'message':    self.message,
            'notif_type': self.notif_type.value,
            'is_read':    self.is_read,
            'created_at': self.created_at.isoformat(),
        }
