# ============================================================
# app/models/student.py — Student Model (Flask-Login user)
# ============================================================
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Student(UserMixin, db.Model):
    __tablename__ = 'students'

    student_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    reg_number  = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name        = db.Column(db.String(100), nullable=False)
    email       = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone       = db.Column(db.String(15))
    password_hash = db.Column(db.String(256), nullable=False)
    dept_id     = db.Column(db.Integer, db.ForeignKey('departments.dept_id'), nullable=False)
    semester    = db.Column(db.Integer, nullable=False, default=1)
    year        = db.Column(db.Integer, nullable=False, default=1)
    photo_path  = db.Column(db.String(255))     # path to stored face photo
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    attendances   = db.relationship('Attendance', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    marks_records = db.relationship('Marks', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    assignments   = db.relationship('Assignment', backref='student', lazy='dynamic')
    face_encodings = db.relationship('FaceEncoding', backref='student', lazy='dynamic', cascade='all, delete-orphan')
    risk_predictions = db.relationship('RiskPrediction', backref='student', lazy='dynamic')
    notifications = db.relationship('Notification', backref='student', lazy='dynamic')

    # ── Flask-Login: override get_id to encode role ─────────────
    def get_id(self):
        return f'student_{self.student_id}'

    # ── Password helpers ─────────────────────────────────────────
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ── Computed properties ──────────────────────────────────────
    @property
    def role(self):
        return 'student'

    def get_attendance_percentage(self, subject_id=None):
        """Return overall or subject-wise attendance percentage."""
        from app.models.attendance import Attendance
        query = self.attendances
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        total = query.count()
        if total == 0:
            return 0.0
        present = query.filter(Attendance.status.in_(['Present', 'Late'])).count()
        return round((present / total) * 100, 2)

    def __repr__(self):
        return f'<Student {self.reg_number} – {self.name}>'

    def to_dict(self):
        return {
            'student_id': self.student_id,
            'reg_number': self.reg_number,
            'name':       self.name,
            'email':      self.email,
            'semester':   self.semester,
            'year':       self.year,
            'is_active':  self.is_active,
        }
