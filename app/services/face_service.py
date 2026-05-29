# ============================================================
# app/services/face_service.py — Face Recognition Service
# Full production implementation using DeepFace + FaceNet512
# OpenCV multi-face detection · confidence scoring ·
# unknown face logging · encoding storage in MySQL (BLOB)
# ============================================================

import os
import warnings
import cv2
import pickle
import logging
import tempfile
import uuid
import numpy as np
from datetime import datetime
from flask import current_app

os.environ.setdefault('TF_USE_LEGACY_KERAS', '1')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
os.environ.setdefault('TF_ENABLE_ONEDNN_OPTS', '0')
os.environ.setdefault('GLOG_minloglevel', '2')

warnings.filterwarnings('ignore', message='.*urllib3.*doesn.*match a supported version.*')
warnings.filterwarnings('ignore', message='.*SymbolDatabase.GetPrototype\\(\\) is deprecated.*')

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────
FACE_MODEL    = 'Facenet512'      # 512-D embeddings, best accuracy
FACE_DETECTOR = 'retinaface'      # Best detector for varied angles
THRESHOLD     = 0.60              # Cosine similarity threshold


class FaceService:
    """
    Full face recognition pipeline:
      1. Detect faces in a frame (OpenCV / RetinaFace)
      2. Generate 512-D embeddings (DeepFace / FaceNet512)
      3. Match against stored encodings (cosine similarity)
      4. Return identity + confidence, or flag as unknown
    """

    # ── Encoding generation ───────────────────────────────────

    @staticmethod
    def generate_encoding(image_path: str) -> np.ndarray | None:
        """
        Generate a 512-D FaceNet embedding for an image file.
        Returns numpy array or None if no face detected.
        """
        try:
            from deepface import DeepFace
            results = DeepFace.represent(
                img_path=image_path,
                model_name=FACE_MODEL,
                detector_backend=FACE_DETECTOR,
                enforce_detection=True,
                align=True,
            )
            if results:
                embedding = np.array(results[0]['embedding'], dtype=np.float32)
                logger.debug(f'Encoding generated for {image_path}: shape={embedding.shape}')
                return embedding
        except Exception as e:
            logger.error(f'Encoding failed for {image_path}: {e}')
        return None

    @staticmethod
    def generate_encoding_from_frame(frame: np.ndarray) -> np.ndarray | None:
        """
        Generate embedding directly from an OpenCV BGR frame.
        Saves frame to a temp file, runs DeepFace, deletes temp file.
        """
        tmp_path = os.path.join(tempfile.gettempdir(), f'_sc_face_{uuid.uuid4().hex}.jpg')
        try:
            if not cv2.imwrite(tmp_path, frame):
                logger.error(f'Failed to write temporary face image: {tmp_path}')
                return None
            return FaceService.generate_encoding(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ── Model training ────────────────────────────────────────

    @staticmethod
    def train_encodings() -> dict:
        """
        Rebuild face encodings for ALL active students who have a photo.
        Deletes old encodings first, then re-generates from photo_path.
        Returns summary dict.
        """
        from app.models.student      import Student
        from app.models.face_encoding import FaceEncoding
        from app import db

        students = Student.query.filter_by(is_active=True).all()
        success_count = 0
        fail_count    = 0
        skipped_count = 0

        for student in students:
            if not student.photo_path or not os.path.exists(student.photo_path):
                logger.warning(f'No photo for {student.reg_number} — skipping')
                skipped_count += 1
                continue

            try:
                embedding = FaceService.generate_encoding(student.photo_path)
                if embedding is None:
                    logger.warning(f'No face found in photo for {student.reg_number}')
                    fail_count += 1
                    continue

                # Replace any existing encoding for this student
                FaceEncoding.query.filter_by(student_id=student.student_id).delete()
                fe = FaceEncoding(
                    user_type='student',
                    user_id=student.student_id,
                    student_id=student.student_id,
                    encoding_data=pickle.dumps(embedding),
                    model_used=FACE_MODEL,
                    image_path=student.photo_path,
                )
                db.session.add(fe)
                success_count += 1
                logger.info(f'Encoding stored for {student.reg_number}')

            except Exception as e:
                logger.error(f'Training error for {student.reg_number}: {e}')
                fail_count += 1

        db.session.commit()
        summary = {
            'count':   success_count,
            'failed':  fail_count,
            'skipped': skipped_count,
            'timestamp': datetime.utcnow().isoformat(),
        }
        logger.info(f'Training complete: {summary}')
        return summary

    # ── Identity matching ─────────────────────────────────────

    @staticmethod
    def identify_face(frame_or_path, threshold: float = None) -> dict:
        """
        Identify a face from an OpenCV frame (np.ndarray) or image path (str).

        Returns:
            {
              'is_known':   bool,
              'student_id': int | None,
              'name':       str | None,
              'reg_number': str | None,
              'confidence': float,
            }
        """
        from app.models.face_encoding import FaceEncoding
        from app.models.student       import Student

        if threshold is None:
            try:
                threshold = current_app.config.get('FACE_RECOGNITION_THRESHOLD', THRESHOLD)
            except RuntimeError:
                threshold = THRESHOLD

        # Generate query embedding
        if isinstance(frame_or_path, np.ndarray):
            query_emb = FaceService.generate_encoding_from_frame(frame_or_path)
        else:
            query_emb = FaceService.generate_encoding(frame_or_path)

        if query_emb is None:
            return {'is_known': False, 'confidence': 0.0, 'student_id': None,
                    'name': None, 'reg_number': None}

        # Load all stored encodings and find best match
        all_encodings = FaceEncoding.query.all()
        best_score    = -1.0
        best_fe       = None

        for fe in all_encodings:
            try:
                stored = pickle.loads(fe.encoding_data)
                score  = FaceService._cosine_similarity(query_emb, stored)
                if score > best_score:
                    best_score = score
                    best_fe    = fe
            except Exception as e:
                logger.error(f'Comparison error for encoding {fe.encoding_id}: {e}')

        if best_fe and best_score >= threshold:
            student = Student.query.get(best_fe.student_id)
            logger.info(f'Identified: {student.reg_number} (confidence={best_score:.4f})')
            return {
                'is_known':   True,
                'student_id': student.student_id,
                'name':       student.name,
                'reg_number': student.reg_number,
                'confidence': round(float(best_score), 4),
            }

        logger.info(f'Unknown face (best_score={best_score:.4f}, threshold={threshold})')
        return {'is_known': False, 'confidence': round(float(best_score), 4),
                'student_id': None, 'name': None, 'reg_number': None}

    # ── Multi-face detection ──────────────────────────────────

    @staticmethod
    def detect_faces_in_frame(frame: np.ndarray) -> list[dict]:
        """
        Detect ALL faces in a single OpenCV frame.
        Returns list of dicts with 'bbox' and 'face_crop' for each face.
        Uses OpenCV DNN face detector (fast, no GPU required).
        """
        h, w = frame.shape[:2]
        faces = []

        try:
            # Use OpenCV Haar cascade as a fast pre-screen
            gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            detections = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
            )

            for (x, y, fw, fh) in detections:
                # Add padding around face crop
                pad    = int(min(fw, fh) * 0.15)
                x1     = max(0, x - pad)
                y1     = max(0, y - pad)
                x2     = min(w, x + fw + pad)
                y2     = min(h, y + fh + pad)
                crop   = frame[y1:y2, x1:x2]
                faces.append({
                    'bbox':      (x1, y1, x2, y2),
                    'face_crop': crop,
                })

        except Exception as e:
            logger.error(f'Face detection error: {e}')

        return faces

    @staticmethod
    def draw_face_annotations(frame: np.ndarray, faces: list[dict]) -> np.ndarray:
        """
        Draw bounding boxes and identity labels on a frame.
        Green box = known, Red box = unknown.
        """
        annotated = frame.copy()
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            identity        = face.get('identity', {})
            is_known        = identity.get('is_known', False)
            name            = identity.get('name', 'Unknown')
            conf            = identity.get('confidence', 0.0)

            # Box colour
            color  = (0, 200, 50) if is_known else (0, 0, 220)
            label  = f"{name} ({conf:.0%})" if is_known else f"Unknown ({conf:.0%})"

            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
            cv2.rectangle(annotated,
                          (x1, y1 - label_size[1] - 8),
                          (x1 + label_size[0] + 4, y1),
                          color, -1)
            cv2.putText(annotated, label,
                        (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)

        return annotated

    # ── Unknown face logging ──────────────────────────────────

    @staticmethod
    def log_unknown_face(frame: np.ndarray, location: str = 'Unknown') -> int:
        """
        Save an unknown face frame to disk and create a SecurityLog entry.
        Returns the new log_id.
        """
        from app.models.security_log import SecurityLog, EventType
        from app import db

        try:
            cfg        = current_app.config
            save_dir   = cfg.get('SECURITY_FOLDER', 'app/static/images/security')
        except RuntimeError:
            save_dir   = 'app/static/images/security'

        os.makedirs(save_dir, exist_ok=True)
        filename   = f"unknown_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        save_path  = os.path.join(save_dir, filename)

        cv2.imwrite(save_path, frame)
        logger.warning(f'Unknown face saved: {save_path}')

        log = SecurityLog(
            event_type=EventType.UNKNOWN_FACE,
            image_path=save_path,
            location=location,
            description='Unrecognised face detected by AI camera.',
            alert_sent=False,
        )
        db.session.add(log)
        db.session.commit()
        return log.log_id

    # ── Math helpers ──────────────────────────────────────────

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Cosine similarity between two embedding vectors (0–1)."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))
