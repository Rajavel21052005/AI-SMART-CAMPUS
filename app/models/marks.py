# ============================================================
# app/models/marks.py — Internal Marks Model
# ============================================================
from app import db
from datetime import datetime


class Marks(db.Model):
    __tablename__ = 'marks'
    __table_args__ = (
        db.UniqueConstraint('student_id', 'subject_id', 'semester', 'year', name='uq_marks_student_subject'),
    )

    mark_id    = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.student_id', ondelete='CASCADE'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.subject_id'), nullable=False)
    semester   = db.Column(db.Integer, nullable=False)
    year       = db.Column(db.Integer, nullable=False)
    cia1       = db.Column(db.Float, default=0.0)    # Continuous Internal Assessment 1
    cia2       = db.Column(db.Float, default=0.0)    # Continuous Internal Assessment 2
    lab_mark   = db.Column(db.Float, default=0.0)
    assignment = db.Column(db.Float, default=0.0)
    total      = db.Column(db.Float, default=0.0)    # Computed: cia1+cia2+lab+assign
    gpa        = db.Column(db.Float, default=0.0)    # Computed GPA for this subject
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def compute_total(self):
        """Recompute total and GPA from components."""
        self.total = round(self.cia1 + self.cia2 + self.lab_mark + self.assignment, 2)
        self.gpa   = self._total_to_gpa(self.total)

    @staticmethod
    def _total_to_gpa(total):
        """Convert total marks (0–100) to GPA (0–10) on 10-point scale."""
        if total >= 91: return 10.0
        if total >= 81: return 9.0
        if total >= 71: return 8.0
        if total >= 61: return 7.0
        if total >= 56: return 6.0
        if total >= 50: return 5.0
        return 0.0

    def to_dict(self):
        return {
            'mark_id':    self.mark_id,
            'student_id': self.student_id,
            'subject_id': self.subject_id,
            'cia1':       self.cia1,
            'cia2':       self.cia2,
            'lab_mark':   self.lab_mark,
            'assignment': self.assignment,
            'total':      self.total,
            'gpa':        self.gpa,
        }
