# ============================================================
# app/models/risk.py — Academic Risk Prediction Model
# ============================================================
import enum
from app import db
from datetime import datetime


class RiskLevel(enum.Enum):
    SAFE     = 'Safe'
    MODERATE = 'Moderate'
    HIGH     = 'High'


class RiskPrediction(db.Model):
    __tablename__ = 'risk_predictions'

    pred_id       = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id    = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    risk_level    = db.Column(db.Enum(RiskLevel), nullable=False)
    attend_pct    = db.Column(db.Float)       # Feature used for prediction
    avg_marks     = db.Column(db.Float)
    assign_pct    = db.Column(db.Float)       # Assignment completion %
    prev_gpa      = db.Column(db.Float)
    lab_score     = db.Column(db.Float)
    model_used    = db.Column(db.String(50))  # e.g. "XGBoost"
    accuracy      = db.Column(db.Float)       # Model accuracy at time of prediction
    confidence    = db.Column(db.Float)       # Prediction confidence probability
    predicted_at  = db.Column(db.DateTime, default=datetime.utcnow)
    notified      = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'pred_id':      self.pred_id,
            'student_id':   self.student_id,
            'risk_level':   self.risk_level.value,
            'attend_pct':   self.attend_pct,
            'avg_marks':    self.avg_marks,
            'confidence':   self.confidence,
            'model_used':   self.model_used,
            'predicted_at': self.predicted_at.isoformat(),
        }
