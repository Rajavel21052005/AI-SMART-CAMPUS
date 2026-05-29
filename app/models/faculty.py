# ============================================================
# app/models/faculty.py — Faculty and Admin models
# ============================================================
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class Faculty(UserMixin, db.Model):
    __tablename__ = 'faculty'

    faculty_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id  = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone        = db.Column(db.String(15))
    password_hash = db.Column(db.String(256), nullable=False)
    dept_id      = db.Column(db.Integer, db.ForeignKey('departments.dept_id'), nullable=False)
    designation  = db.Column(db.String(100))
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    subjects = db.relationship('Subject', backref='faculty', lazy='dynamic')

    def get_id(self):
        return f'faculty_{self.faculty_id}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role(self):
        return 'faculty'

    def __repr__(self):
        return f'<Faculty {self.employee_id} – {self.name}>'

    def to_dict(self):
        return {
            'faculty_id':  self.faculty_id,
            'employee_id': self.employee_id,
            'name':        self.name,
            'email':       self.email,
            'designation': self.designation,
        }


class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'

    admin_id     = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username     = db.Column(db.String(50), unique=True, nullable=False)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active    = db.Column(db.Boolean, default=True)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)

    def get_id(self):
        return f'admin_{self.admin_id}'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def role(self):
        return 'admin'

    def __repr__(self):
        return f'<Admin {self.username}>'
