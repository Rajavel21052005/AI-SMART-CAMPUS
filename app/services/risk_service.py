# ============================================================
# app/services/risk_service.py — Academic Risk Prediction
# Trains and uses ML models to predict at-risk students.
# Phase 9 adds full training; stubs + structure here.
# ============================================================
import os
import pickle
import logging
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join('ai_models', 'risk_model.pkl')
SCALER_PATH = os.path.join('ai_models', 'risk_scaler.pkl')


class RiskService:
    """
    Predicts academic risk (Safe / Moderate / High) for students.
    Features: attendance_pct, avg_marks, assignment_completion,
              prev_gpa, lab_score.
    Models compared: Random Forest, XGBoost, Logistic Regression.
    Best model saved to ai_models/risk_model.pkl
    """

    # ── Feature extraction ────────────────────────────────────

    @staticmethod
    def extract_features(student_id: int) -> dict:
        """
        Build the feature vector for a student from the database.
        Returns dict with feature names and values.
        """
        from app.models.student import Student
        from app.models.attendance import Attendance, AttendanceStatus
        from app.models.marks import Marks
        from app.models.assignment import Assignment, SubmissionStatus
        from app import db

        student = Student.query.get(student_id)
        if not student:
            raise ValueError(f'Student {student_id} not found')

        # 1. Attendance percentage
        total   = Attendance.query.filter_by(student_id=student_id).count()
        present = Attendance.query.filter_by(student_id=student_id).filter(
            Attendance.status.in_([AttendanceStatus.PRESENT, AttendanceStatus.LATE])
        ).count()
        attend_pct = round((present / total) * 100, 2) if total > 0 else 0.0

        # 2. Average internal marks (current semester)
        marks = Marks.query.filter_by(student_id=student_id, semester=student.semester).all()
        avg_marks = round(np.mean([m.total for m in marks]), 2) if marks else 0.0

        # 3. Assignment completion %
        total_assign  = Assignment.query.filter_by(student_id=student_id).count()
        submitted     = Assignment.query.filter_by(student_id=student_id, status=SubmissionStatus.SUBMITTED).count()
        assign_pct    = round((submitted / total_assign) * 100, 2) if total_assign > 0 else 0.0

        # 4. Previous semester GPA (last semester marks)
        prev_marks = Marks.query.filter_by(
            student_id=student_id,
            semester=max(1, student.semester - 1)
        ).all()
        prev_gpa = round(np.mean([m.gpa for m in prev_marks]), 2) if prev_marks else 0.0

        # 5. Lab score (average of lab marks this semester)
        lab_scores = [m.lab_mark for m in marks if m.lab_mark is not None]
        lab_score  = round(np.mean(lab_scores), 2) if lab_scores else 0.0

        return {
            'attend_pct':  attend_pct,
            'avg_marks':   avg_marks,
            'assign_pct':  assign_pct,
            'prev_gpa':    prev_gpa,
            'lab_score':   lab_score,
        }

    # ── Prediction ────────────────────────────────────────────

    @staticmethod
    def predict_for_student(student_id: int) -> dict:
        """
        Run risk prediction for a single student.
        Saves result to DB and returns prediction dict.
        """
        from app.models.risk import RiskPrediction, RiskLevel
        from app import db

        features = RiskService.extract_features(student_id)

        if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
            risk_label, confidence, model_name = RiskService._run_model(features)
        else:
            # Fallback: rule-based prediction (before model is trained)
            risk_label, confidence, model_name = RiskService._rule_based(features)

        # Map string to enum
        risk_map = {'Safe': RiskLevel.SAFE, 'Moderate': RiskLevel.MODERATE, 'High': RiskLevel.HIGH}
        risk_enum = risk_map.get(risk_label, RiskLevel.MODERATE)

        # Save to DB
        pred = RiskPrediction(
            student_id=student_id,
            risk_level=risk_enum,
            attend_pct=features['attend_pct'],
            avg_marks=features['avg_marks'],
            assign_pct=features['assign_pct'],
            prev_gpa=features['prev_gpa'],
            lab_score=features['lab_score'],
            model_used=model_name,
            confidence=confidence,
        )
        db.session.add(pred)
        db.session.commit()

        return {**pred.to_dict(), **features}

    @staticmethod
    def _run_model(features: dict):
        """Load saved model and scaler, run prediction."""
        with open(MODEL_PATH, 'rb') as f:
            model = pickle.load(f)
        with open(SCALER_PATH, 'rb') as f:
            scaler = pickle.load(f)

        X = np.array([[
            features['attend_pct'],
            features['avg_marks'],
            features['assign_pct'],
            features['prev_gpa'],
            features['lab_score'],
        ]])
        X_scaled = scaler.transform(X)
        pred_idx  = model.predict(X_scaled)[0]
        proba     = model.predict_proba(X_scaled)[0]
        labels    = ['Safe', 'Moderate', 'High']
        return labels[pred_idx], round(float(np.max(proba)), 4), type(model).__name__

    @staticmethod
    def _rule_based(features: dict):
        """
        Simple rule-based fallback before the ML model is trained.
        High risk: attendance < 60% OR marks < 40
        Moderate:  attendance < 75% OR marks < 55
        Safe:      otherwise
        """
        a = features['attend_pct']
        m = features['avg_marks']
        if a < 60 or m < 40:
            return 'High', 0.85, 'RuleBased'
        elif a < 75 or m < 55:
            return 'Moderate', 0.75, 'RuleBased'
        return 'Safe', 0.90, 'RuleBased'
