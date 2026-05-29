# ============================================================
# app/models/timetable.py — Timetable Model
# ============================================================
import enum
from app import db


class DayOfWeek(enum.Enum):
    MONDAY    = 'Monday'
    TUESDAY   = 'Tuesday'
    WEDNESDAY = 'Wednesday'
    THURSDAY  = 'Thursday'
    FRIDAY    = 'Friday'
    SATURDAY  = 'Saturday'


class Timetable(db.Model):
    __tablename__ = 'timetable'
    __table_args__ = (
        db.UniqueConstraint('dept_id', 'semester', 'day', 'period_number', name='uq_timetable_slot'),
    )

    tt_id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    dept_id       = db.Column(db.Integer, db.ForeignKey('departments.dept_id'), nullable=False)
    semester      = db.Column(db.Integer, nullable=False)
    subject_id    = db.Column(db.Integer, db.ForeignKey('subjects.subject_id'), nullable=False)
    faculty_id    = db.Column(db.Integer, db.ForeignKey('faculty.faculty_id'))
    day           = db.Column(db.Enum(DayOfWeek), nullable=False)
    period_number = db.Column(db.Integer, nullable=False)  # 1–8
    start_time    = db.Column(db.Time, nullable=False)
    end_time      = db.Column(db.Time, nullable=False)
    room          = db.Column(db.String(20))

    def to_dict(self):
        return {
            'tt_id':         self.tt_id,
            'day':           self.day.value,
            'period_number': self.period_number,
            'start_time':    str(self.start_time),
            'end_time':      str(self.end_time),
            'subject_id':    self.subject_id,
            'room':          self.room,
        }
