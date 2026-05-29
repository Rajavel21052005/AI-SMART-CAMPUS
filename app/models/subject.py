# ============================================================
# app/models/subject.py — Subject Model
# ============================================================
from app import db
from datetime import datetime


class Subject(db.Model):
    __tablename__ = 'subjects'

    subject_id  = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code        = db.Column(db.String(20), unique=True, nullable=False)
    name        = db.Column(db.String(150), nullable=False)
    credits     = db.Column(db.Integer, default=3)
    dept_id     = db.Column(db.Integer, db.ForeignKey('departments.dept_id'), nullable=False)
    faculty_id  = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'))
    semester    = db.Column(db.Integer, nullable=False)
    is_lab      = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    attendances = db.relationship('Attendance', backref='subject', lazy='dynamic')
    timetables  = db.relationship('Timetable', backref='subject', lazy='dynamic')
    marks       = db.relationship('Marks', backref='subject', lazy='dynamic')

    def __repr__(self):
        return f'<Subject {self.code} – {self.name}>'

    def to_dict(self):
        return {
            'subject_id': self.subject_id,
            'code':       self.code,
            'name':       self.name,
            'credits':    self.credits,
            'semester':   self.semester,
            'is_lab':     self.is_lab,
        }
