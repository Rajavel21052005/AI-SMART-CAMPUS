# ============================================================
# app/models/security_log.py — Campus Security Log
# ============================================================
import enum
from app import db
from datetime import datetime


class EventType(enum.Enum):
    UNKNOWN_FACE  = 'unknown_face'
    SPOOF_ATTEMPT = 'spoof_attempt'
    FORCED_ENTRY  = 'forced_entry'
    SYSTEM_ALERT  = 'system_alert'


class SecurityLog(db.Model):
    __tablename__ = 'security_logs'
    __table_args__ = (db.Index('ix_security_timestamp', 'timestamp'),)

    log_id      = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type  = db.Column(db.Enum(EventType), nullable=False)
    image_path  = db.Column(db.String(255))   # Saved frame from camera
    location    = db.Column(db.String(100))   # e.g. "Main Gate", "Lab 3"
    camera_id   = db.Column(db.String(50))
    description = db.Column(db.Text)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    alert_sent  = db.Column(db.Boolean, default=False)
    resolved    = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'log_id':      self.log_id,
            'event_type':  self.event_type.value,
            'location':    self.location,
            'timestamp':   self.timestamp.isoformat(),
            'alert_sent':  self.alert_sent,
            'resolved':    self.resolved,
        }
