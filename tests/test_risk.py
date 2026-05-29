# ============================================================
# tests/test_risk.py — Risk Prediction & ML Tests
# ============================================================
import pytest
import numpy as np
from app import create_app, db
from app.models.department import Department
from app.models.student    import Student
from app.models.subject    import Subject
from app.models.marks      import Marks
from app.models.attendance import Attendance, AttendanceStatus
from app.services.risk_service import RiskService
from config.config import TestingConfig
from datetime import date, timedelta


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        dept    = Department(name='Test Dept', code='TST')
        db.session.add(dept)
        db.session.flush()

        student = Student(reg_number='22TS001', name='Test Student',
                          email='test@ts.edu', dept_id=dept.dept_id,
                          semester=3, year=2)
        student.set_password('Test@1234')
        db.session.add(student)

        subj = Subject(code='TS301', name='Test Subject', credits=3,
                       dept_id=dept.dept_id, semester=3)
        db.session.add(subj)
        db.session.flush()

        # 20 days of attendance: 15 Present, 5 Absent  (75%)
        today = date.today()
        for i in range(20):
            d   = today - timedelta(days=i)
            status = AttendanceStatus.PRESENT if i < 15 else AttendanceStatus.ABSENT
            db.session.add(Attendance(student_id=student.student_id,
                                       subject_id=subj.subject_id,
                                       date=d, status=status))

        # Marks
        m = Marks(student_id=student.student_id, subject_id=subj.subject_id,
                  semester=3, year=2, cia1=25, cia2=22, lab_mark=20, assignment=8)
        m.compute_total()
        db.session.add(m)
        db.session.commit()
        yield app
        db.drop_all()


def test_rule_based_safe():
    label, conf, model = RiskService._rule_based(
        {'attend_pct': 90, 'avg_marks': 75, 'assign_pct': 95, 'prev_gpa': 8.5, 'lab_score': 85}
    )
    assert label == 'Safe'
    assert conf > 0.5


def test_rule_based_moderate():
    label, conf, model = RiskService._rule_based(
        {'attend_pct': 70, 'avg_marks': 52, 'assign_pct': 60, 'prev_gpa': 5.5, 'lab_score': 55}
    )
    assert label == 'Moderate'


def test_rule_based_high():
    label, conf, model = RiskService._rule_based(
        {'attend_pct': 45, 'avg_marks': 30, 'assign_pct': 30, 'prev_gpa': 3.0, 'lab_score': 35}
    )
    assert label == 'High'


def test_extract_features(app):
    with app.app_context():
        student = Student.query.first()
        features = RiskService.extract_features(student.student_id)
        assert 'attend_pct' in features
        assert 'avg_marks'  in features
        assert 0 <= features['attend_pct'] <= 100
        assert features['avg_marks'] > 0


def test_predict_saves_to_db(app):
    with app.app_context():
        from app.models.risk import RiskPrediction
        student = Student.query.first()
        result  = RiskService.predict_for_student(student.student_id)
        assert 'risk_level' in result
        assert result['risk_level'] in ('Safe', 'Moderate', 'High')

        saved = RiskPrediction.query.filter_by(student_id=student.student_id).first()
        assert saved is not None
        assert saved.model_used is not None


def test_synthetic_data_generation():
    """Training script should generate valid DataFrame."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from training.train_risk_model import generate_synthetic_data
    df = generate_synthetic_data(n=100)
    assert len(df) == 100
    assert set(df.columns) >= {'attend_pct', 'avg_marks', 'assign_pct', 'prev_gpa', 'lab_score', 'risk_label'}
    assert df['risk_label'].isin([0, 1, 2]).all()


def test_model_trains_and_predicts():
    """Full train → predict pipeline with synthetic data."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from training.train_risk_model import generate_synthetic_data, train_and_evaluate
    df     = generate_synthetic_data(n=200)
    result = train_and_evaluate(df)
    assert result['best_f1'] > 0.5
    assert result['best_name'] in ('RandomForest', 'XGBoost', 'LogisticRegression')
    for name, res in result['results'].items():
        assert 0 < res['accuracy'] <= 1
        assert 0 < res['f1_score'] <= 1
