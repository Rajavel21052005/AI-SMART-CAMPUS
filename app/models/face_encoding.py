# ============================================================
# app/models/face_encoding.py — Face Encoding Storage
# ============================================================
from app import db
from datetime import datetime


class FaceEncoding(db.Model):
    __tablename__ = 'face_encodings'

    encoding_id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_type     = db.Column(db.String(20), nullable=False, default='student')
    user_id       = db.Column(db.Integer, nullable=False)
    student_id    = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    encoding_data = db.Column(db.LargeBinary(length=65535), nullable=False)  # Pickled numpy array
    model_used    = db.Column(db.String(50), default='Facenet512')
    image_path    = db.Column(db.String(255))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<FaceEncoding student_id={self.student_id} model={self.model_used}>'
