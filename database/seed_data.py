# ============================================================
# database/seed_data.py — Seed realistic demo data
# Creates departments, faculty, students, subjects, timetable,
# attendance records, marks, and risk predictions for testing.
#
# Usage (from project root):
#   python database/seed_data.py
# ============================================================
import sys, os, random
from datetime import date, timedelta, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.department  import Department
from app.models.faculty     import Faculty
from app.models.student     import Student
from app.models.subject     import Subject
from app.models.attendance  import Attendance, AttendanceStatus
from app.models.marks       import Marks
from app.models.assignment  import Assignment, SubmissionStatus
from app.models.timetable   import Timetable, DayOfWeek
from app.models.risk        import RiskPrediction, RiskLevel
from app.models.notification import Notification, NotificationType

app = create_app()

DEPARTMENTS = [
    {"name": "Computer Science Engineering", "code": "CSE", "hod": "Dr. R. Krishnamurthy"},
    {"name": "Electronics & Communication",  "code": "ECE", "hod": "Dr. S. Meenakshi"},
    {"name": "Mechanical Engineering",       "code": "MECH","hod": "Dr. P. Anbazhagan"},
    {"name": "Master of Computer Applications", "code": "MCA", "hod": "Dr. K. Szenthil"},
]

FACULTY_DATA = [
    {"employee_id":"FAC001","name":"Prof. Arun Kumar",    "email":"arun@campus.edu","dept":"CSE","designation":"Assistant Professor"},
    {"employee_id":"FAC002","name":"Prof. Priya Sharma",  "email":"priya@campus.edu","dept":"CSE","designation":"Associate Professor"},
    {"employee_id":"FAC003","name":"Prof. Ravi Sundar",   "email":"ravi@campus.edu", "dept":"ECE","designation":"Assistant Professor"},
    {"employee_id":"FAC004","name":"Prof. Senthil Kumar", "email":"senthil@campus.edu", "dept":"MCA","designation":"ASSOCIATE Professor"},
]

SUBJECTS_DATA = [
    {"code":"CS301","name":"Data Structures","credits":4,"dept":"CSE","sem":3,"faculty":"FAC001"},
    {"code":"CS302","name":"Database Management","credits":3,"dept":"CSE","sem":3,"faculty":"FAC002"},
    {"code":"CS303","name":"Operating Systems","credits":3,"dept":"CSE","sem":3,"faculty":"FAC001"},
    {"code":"CS304","name":"Computer Networks","credits":3,"dept":"CSE","sem":3,"faculty":"FAC002"},
    {"code":"CS305","name":"Web Technologies Lab","credits":2,"dept":"CSE","sem":3,"faculty":"FAC001","lab":True},
]

STUDENTS_DATA = [
    {"reg":"22CS001","name":"Arjun Ramesh",    "email":"arjun@student.campus.edu",  "dept":"CSE","sem":3,"year":2},
    {"reg":"22CS002","name":"Priya Venkat",    "email":"priya.v@student.campus.edu","dept":"CSE","sem":3,"year":2},
    {"reg":"22CS003","name":"Karthik Suresh",  "email":"karthik@student.campus.edu","dept":"CSE","sem":3,"year":2},
    {"reg":"22CS004","name":"Divya Nair",      "email":"divya@student.campus.edu",  "dept":"CSE","sem":3,"year":2},
    {"reg":"22CS005","name":"Aravind Pillai",  "email":"aravind@student.campus.edu","dept":"CSE","sem":3,"year":2},
    {"reg":"22CS006","name":"Sneha Krishnan",  "email":"sneha@student.campus.edu",  "dept":"CSE","sem":3,"year":2},
    {"reg":"22CS007","name":"Rahul Menon",     "email":"rahul@student.campus.edu",  "dept":"CSE","sem":3,"year":2},
    {"reg":"22CS008","name":"Anjali Mohan",    "email":"anjali@student.campus.edu", "dept":"CSE","sem":3,"year":2},
    {"reg":"22CS009","name":"Rishika k",    "email":"rishika@student.campus.edu", "dept":"CSE","sem":3,"year":2},
]

TIMETABLE_DATA = [
    # (day, period, subject_code, start, end, room)
    ("Monday",    1, "CS301", "09:00", "09:50", "A101"),
    ("Monday",    2, "CS302", "09:50", "10:40", "A101"),
    ("Monday",    3, "CS303", "10:50", "11:40", "A101"),
    ("Tuesday",   1, "CS304", "09:00", "09:50", "A102"),
    ("Tuesday",   2, "CS301", "09:50", "10:40", "A102"),
    ("Tuesday",   3, "CS305", "10:50", "12:30", "Lab1"),
    ("Wednesday", 1, "CS302", "09:00", "09:50", "A101"),
    ("Wednesday", 2, "CS303", "09:50", "10:40", "A101"),
    ("Thursday",  1, "CS301", "09:00", "09:50", "A101"),
    ("Thursday",  2, "CS304", "09:50", "10:40", "A101"),
    ("Friday",    1, "CS303", "09:00", "09:50", "A102"),
    ("Friday",    2, "CS302", "09:50", "10:40", "A102"),
]


def run():
    with app.app_context():
        print("Seeding Smart Campus database...")

        # ── Departments ───────────────────────────────────────
        dept_map = {}
        for d in DEPARTMENTS:
            dept = Department.query.filter_by(code=d["code"]).first()
            if not dept:
                dept = Department(name=d["name"], code=d["code"], hod_name=d["hod"])
                db.session.add(dept)
                db.session.flush()
            dept_map[d["code"]] = dept
        db.session.commit()
        print(f"  OK {len(DEPARTMENTS)} departments")

        # ── Faculty ───────────────────────────────────────────
        faculty_map = {}
        for f in FACULTY_DATA:
            fac = Faculty.query.filter_by(employee_id=f["employee_id"]).first()
            if not fac:
                fac = Faculty(
                    employee_id=f["employee_id"], name=f["name"],
                    email=f["email"], dept_id=dept_map[f["dept"]].dept_id,
                    designation=f["designation"]
                )
                fac.set_password("Faculty@1234")
                db.session.add(fac)
                db.session.flush()
            faculty_map[f["employee_id"]] = fac
        db.session.commit()
        print(f"  OK {len(FACULTY_DATA)} faculty accounts seeded")

        # ── Subjects ──────────────────────────────────────────
        subject_map = {}
        for s in SUBJECTS_DATA:
            subj = Subject.query.filter_by(code=s["code"]).first()
            if not subj:
                subj = Subject(
                    code=s["code"], name=s["name"], credits=s["credits"],
                    dept_id=dept_map[s["dept"]].dept_id,
                    faculty_id=faculty_map[s["faculty"]].faculty_id,
                    semester=s["sem"], is_lab=s.get("lab", False)
                )
                db.session.add(subj)
                db.session.flush()
            subject_map[s["code"]] = subj
        db.session.commit()
        print(f"  OK {len(SUBJECTS_DATA)} subjects")

        # ── Timetable ─────────────────────────────────────────
        cse_dept = dept_map["CSE"]
        for item in TIMETABLE_DATA:
            if not isinstance(item, tuple):
                continue
            day_str, period, subj_code, start_str, end_str, room = item
            day_enum = DayOfWeek[day_str.upper()]
            exists   = Timetable.query.filter_by(
                dept_id=cse_dept.dept_id, semester=3,
                day=day_enum, period_number=period
            ).first()
            if not exists:
                h1,m1 = map(int, start_str.split(":"))
                h2,m2 = map(int, end_str.split(":"))
                tt = Timetable(
                    dept_id=cse_dept.dept_id, semester=3,
                    subject_id=subject_map[subj_code].subject_id,
                    faculty_id=subject_map[subj_code].faculty_id,
                    day=day_enum, period_number=period,
                    start_time=time(h1, m1), end_time=time(h2, m2),
                    room=room
                )
                db.session.add(tt)
        db.session.commit()
        print(f"  OK {len([item for item in TIMETABLE_DATA if isinstance(item, tuple)])} timetable slots")

        # ── Students ──────────────────────────────────────────
        student_objs = []
        for s in STUDENTS_DATA:
            st = Student.query.filter_by(reg_number=s["reg"]).first()
            if not st:
                st = Student(
                    reg_number=s["reg"], name=s["name"], email=s["email"],
                    dept_id=dept_map[s["dept"]].dept_id,
                    semester=s["sem"], year=s["year"]
                )
                st.set_password("Student@1234")
                db.session.add(st)
                db.session.flush()
            student_objs.append(st)
        db.session.commit()
        print(f"  OK {len(STUDENTS_DATA)} students seeded")

        # ── Attendance (last 30 days) ─────────────────────────
        subjects = list(subject_map.values())
        attend_count = 0
        today        = date.today()

        for student in student_objs:
            # Give each student a random "reliability" score (0.5–1.0)
            reliability = random.uniform(0.5, 1.0)
            for subj in subjects:
                for days_ago in range(30, 0, -1):
                    class_date = today - timedelta(days=days_ago)
                    if class_date.weekday() >= 5:   # Skip weekends
                        continue
                    if Attendance.query.filter_by(
                        student_id=student.student_id,
                        subject_id=subj.subject_id, date=class_date
                    ).first():
                        continue

                    rand = random.random()
                    if rand < reliability * 0.80:
                        status = AttendanceStatus.PRESENT
                    elif rand < reliability * 0.90:
                        status = AttendanceStatus.LATE
                    else:
                        status = AttendanceStatus.ABSENT

                    att = Attendance(
                        student_id=student.student_id,
                        subject_id=subj.subject_id,
                        date=class_date,
                        time_in=None if status == AttendanceStatus.ABSENT else
                                __import__('datetime').datetime.combine(
                                    class_date,
                                    time(9, random.randint(0, 20))
                                ),
                        status=status,
                        confidence_score=round(random.uniform(0.72, 0.99), 3)
                            if status != AttendanceStatus.ABSENT else None
                    )
                    db.session.add(att)
                    attend_count += 1

        db.session.commit()
        print(f"  OK {attend_count} attendance records (30 days)")

        # ── Marks ─────────────────────────────────────────────
        marks_count = 0
        for student in student_objs:
            for subj in subjects:
                exists = Marks.query.filter_by(
                    student_id=student.student_id,
                    subject_id=subj.subject_id, semester=3
                ).first()
                if not exists:
                    m = Marks(
                        student_id=student.student_id,
                        subject_id=subj.subject_id, semester=3, year=2,
                        cia1=round(random.uniform(10, 30), 1),
                        cia2=round(random.uniform(10, 30), 1),
                        lab_mark=round(random.uniform(15, 25), 1),
                        assignment=round(random.uniform(5, 10), 1),
                    )
                    m.compute_total()
                    db.session.add(m)
                    marks_count += 1
        db.session.commit()
        print(f"  OK {marks_count} marks records")

        # ── Assignments ───────────────────────────────────────
        assign_count = 0
        for student in student_objs[:4]:
            for subj in subjects[:3]:
                due = today + timedelta(days=random.randint(1, 14))
                a   = Assignment(
                    title=f"{subj.code} Assignment {random.randint(1,3)}",
                    subject_id=subj.subject_id,
                    student_id=student.student_id,
                    due_date=__import__('datetime').datetime.combine(due, time(23, 59)),
                    status=SubmissionStatus.PENDING,
                    max_marks=10
                )
                db.session.add(a)
                assign_count += 1
        db.session.commit()
        print(f"  OK {assign_count} pending assignments")

        # ── Risk predictions (rule-based seed) ───────────────
        risk_count = 0
        for student in student_objs:
            attend_pct = student.get_attendance_percentage()
            all_marks  = Marks.query.filter_by(student_id=student.student_id, semester=3).all()
            avg_marks  = round(sum(m.total for m in all_marks) / len(all_marks), 1) if all_marks else 0

            if attend_pct < 60 or avg_marks < 40:
                risk = RiskLevel.HIGH
            elif attend_pct < 75 or avg_marks < 55:
                risk = RiskLevel.MODERATE
            else:
                risk = RiskLevel.SAFE

            pred = RiskPrediction(
                student_id=student.student_id,
                risk_level=risk,
                attend_pct=attend_pct, avg_marks=avg_marks,
                assign_pct=70.0, prev_gpa=7.0, lab_score=75.0,
                model_used="RuleBased", confidence=0.80
            )
            db.session.add(pred)

            if risk == RiskLevel.HIGH:
                notif = Notification(
                    student_id=student.student_id,
                    title="⚠️ Academic Risk Alert",
                    message=f"Your attendance is {attend_pct:.1f}% and average marks are {avg_marks}. Please meet your advisor immediately.",
                    notif_type=NotificationType.HIGH_RISK
                )
                db.session.add(notif)
            risk_count += 1

        db.session.commit()
        print(f"  OK {risk_count} risk predictions")

        print("\nSeed complete! Demo data inserted.")


if __name__ == "__main__":
    run()
