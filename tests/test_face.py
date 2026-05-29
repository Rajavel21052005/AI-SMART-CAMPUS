# ============================================================
# tests/test_face.py — Face Service Unit Tests
# (Tests encoding helpers that don't require a camera/GPU)
# ============================================================
import numpy as np
import pytest
from app import create_app, db
from app.models.face_encoding import FaceEncoding
from app.services.face_service import FaceService
from config.config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_face_encoding_persists_owner_metadata(app):
    with app.app_context():
        encoding = FaceEncoding(
            user_type='student',
            user_id=8,
            student_id=8,
            encoding_data=b'encoded-data',
            model_used='Facenet512',
            image_path='app/static/images/uploads/students/22CS008/test.jpeg',
        )
        db.session.add(encoding)
        db.session.commit()

        stored = FaceEncoding.query.filter_by(student_id=8).first()
        assert stored is not None
        assert stored.user_type == 'student'
        assert stored.user_id == 8


def test_cosine_similarity_identical():
    """Identical vectors should give similarity of 1.0."""
    v = np.array([0.5, 0.3, 0.8, 0.1])
    assert abs(FaceService._cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal():
    """Orthogonal vectors should give similarity of 0.0."""
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(FaceService._cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_zero_vector():
    """Zero vector input should return 0.0 without crashing."""
    a = np.array([0.0, 0.0])
    b = np.array([1.0, 0.5])
    assert FaceService._cosine_similarity(a, b) == 0.0


def test_rule_based_risk_high():
    """Rule-based fallback: attendance < 60% → HIGH."""
    from app.services.risk_service import RiskService
    label, conf, model = RiskService._rule_based({'attend_pct': 55, 'avg_marks': 30, 'assign_pct': 50, 'prev_gpa': 5, 'lab_score': 40})
    assert label == 'High'


def test_rule_based_risk_safe():
    """Rule-based fallback: good metrics → SAFE."""
    from app.services.risk_service import RiskService
    label, conf, model = RiskService._rule_based({'attend_pct': 90, 'avg_marks': 80, 'assign_pct': 95, 'prev_gpa': 8.5, 'lab_score': 85})
    assert label == 'Safe'
