# ============================================================
# app/models/department.py — Department Model
# ============================================================
from app import db
from datetime import datetime


class Department(db.Model):
    __tablename__ = 'departments'

    dept_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name      = db.Column(db.String(100), nullable=False, unique=True)
    code      = db.Column(db.String(10),  nullable=False, unique=True)   # e.g. "CSE"
    hod_name  = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    students = db.relationship('Student', backref='department', lazy='dynamic')
    faculty  = db.relationship('Faculty', backref='department', lazy='dynamic')
    subjects = db.relationship('Subject', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.code}>'

    def to_dict(self):
        return {
            'dept_id':   self.dept_id,
            'name':      self.name,
            'code':      self.code,
            'hod_name':  self.hod_name,
        }
