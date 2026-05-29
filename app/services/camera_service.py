# ============================================================
# app/services/camera_service.py — Webcam Capture Pipeline
# Runs the full recognition loop:
#   capture → liveness → spoof check → identify → mark attendance
# Streams MJPEG frames to the browser via Flask route.
# ============================================================

import cv2
import logging
import time
import numpy as np
from datetime import datetime
from flask import current_app

from app.services.face_service             import FaceService
from app.services.liveness.liveness_detector import LivenessDetector
from app.services.liveness.spoof_detector    import SpoofDetector
from app.services.attendance_service        import AttendanceService

logger = logging.getLogger(__name__)

# ── Module-level camera state ─────────────────────────────────
_camera     = None   # cv2.VideoCapture instance
_is_running = False


def get_camera() -> cv2.VideoCapture | None:
    """Return the shared VideoCapture instance, opening it if needed."""
    global _camera
    if _camera is None or not _camera.isOpened():
        _camera = cv2.VideoCapture(0)                  # camera index 0
        _camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        _camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        _camera.set(cv2.CAP_PROP_FPS, 30)
        if not _camera.isOpened():
            logger.error('Cannot open camera — check device permissions')
            _camera = None
    return _camera


def release_camera():
    """Release webcam when no longer needed."""
    global _camera
    if _camera and _camera.isOpened():
        _camera.release()
        _camera = None
    logger.info('Camera released')


# ── MJPEG frame generator for Flask streaming ─────────────────

def generate_frames(subject_id: int, mode: str = 'attendance'):
    """
    Generator that yields MJPEG boundary frames for use with
    Flask's Response(stream_with_context(...)).

    Args:
        subject_id: Subject to mark attendance for
        mode:       'attendance' | 'register' | 'security'

    Yields:
        bytes — MJPEG frame boundary
    """
    cam = get_camera()
    if cam is None:
        yield _error_frame('Camera unavailable')
        return

    liveness = LivenessDetector(required_blinks=2)
    spoof    = SpoofDetector()

    # Track students already processed this session (prevent duplicate API calls)
    processed_this_session: set[int] = set()

    # Per-student cooldown: once identified, wait before re-checking
    last_identified: dict[int, float] = {}
    COOLDOWN_SECONDS = 8.0

    logger.info(f'Camera stream started — subject={subject_id} mode={mode}')

    try:
        while True:
            ret, frame = cam.read()
            if not ret or frame is None:
                logger.warning('Failed to grab frame')
                time.sleep(0.05)
                continue

            annotated = frame.copy()

            # ── Detect all faces in the frame ─────────────────
            faces = FaceService.detect_faces_in_frame(frame)

            for face_info in faces:
                x1, y1, x2, y2 = face_info['bbox']
                crop            = face_info['face_crop']

                # ── Spoof check (passive, every frame) ────────
                spoof_result = spoof.analyse_frame(crop)
                if spoof_result['is_spoof']:
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    _put_label(annotated, f"SPOOF: {spoof_result['reason'][:30]}",
                               x1, y1 - 10, (0, 0, 255))
                    _log_spoof_attempt(frame)
                    continue

                # ── Liveness check (stateful, per session) ────
                liveness_result = liveness.process_frame(frame)
                _put_label(annotated, liveness_result['message'], 10, 30, (0, 200, 255))

                if liveness_result['failed']:
                    _put_label(annotated, '⚠ LIVENESS FAILED', 10, 60, (0, 0, 255))
                    liveness.reset()
                    continue

                if not liveness_result['verified']:
                    # Still completing liveness — show blink progress
                    blinks_needed = 2 - liveness_result['blinks']
                    _put_label(annotated,
                               f"Blinks remaining: {max(0, blinks_needed)}",
                               10, 60, (200, 200, 0))
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (200, 200, 0), 2)
                    continue

                # ── Liveness passed → Identify face ───────────
                now = time.time()
                identity = FaceService.identify_face(crop)

                if identity['is_known']:
                    sid = identity['student_id']

                    # Respect per-student cooldown
                    if now - last_identified.get(sid, 0) < COOLDOWN_SECONDS:
                        _draw_known(annotated, x1, y1, x2, y2, identity, already=True)
                        continue

                    last_identified[sid] = now

                    # Mark attendance (only once per subject-per-day)
                    if mode == 'attendance' and sid not in processed_this_session:
                        try:
                            record = AttendanceService.mark_attendance(
                                student_id=sid,
                                subject_id=subject_id,
                                confidence=identity['confidence'],
                            )
                            processed_this_session.add(sid)
                            logger.info(
                                f"Attendance marked: {identity['reg_number']} "
                                f"status={record.status.value}"
                            )
                        except Exception as e:
                            logger.error(f'Attendance marking failed: {e}')

                    _draw_known(annotated, x1, y1, x2, y2, identity)

                else:
                    # Unknown face
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 220), 2)
                    _put_label(annotated, f"Unknown ({identity['confidence']:.0%})",
                               x1, y1 - 10, (0, 0, 220))

                    if mode in ('attendance', 'security'):
                        FaceService.log_unknown_face(crop, location='Classroom')

            # ── Overlay HUD ────────────────────────────────────
            _draw_hud(annotated, len(faces), len(processed_this_session))

            # ── Encode as JPEG and yield MJPEG chunk ──────────
            ok, buffer = cv2.imencode('.jpg', annotated, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ok:
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n'
                + buffer.tobytes()
                + b'\r\n'
            )

    except GeneratorExit:
        logger.info('Stream client disconnected')
    except Exception as e:
        logger.error(f'Stream error: {e}')
    finally:
        logger.info('Camera stream generator exiting')


# ── Drawing helpers ───────────────────────────────────────────

def _put_label(frame, text: str, x: int, y: int, color=(255, 255, 255)):
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)   # shadow
    cv2.putText(frame, text, (x, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)


def _draw_known(frame, x1, y1, x2, y2, identity: dict, already: bool = False):
    """Draw a green box with student name and confidence."""
    color = (0, 180, 50)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    label = (f"✓ {identity['name']} ({identity['confidence']:.0%})"
             + (' [logged]' if already else ''))
    _put_label(frame, label, x1, y1 - 10, color)


def _draw_hud(frame, face_count: int, marked_count: int):
    """Draw a semi-transparent HUD with stats."""
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h - 40), (w, h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)
    ts  = datetime.now().strftime('%H:%M:%S')
    hud = f'  Faces: {face_count}   Marked: {marked_count}   {ts}'
    cv2.putText(frame, hud, (8, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 200), 1)


def _error_frame(msg: str) -> bytes:
    """Generate a single black error frame."""
    img  = np.zeros((240, 320, 3), dtype=np.uint8)
    cv2.putText(img, msg, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 1)
    _, buf = cv2.imencode('.jpg', img)
    return (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' +
            buf.tobytes() + b'\r\n')


def _log_spoof_attempt(frame: np.ndarray):
    """Save a spoof-attempt frame to security logs."""
    try:
        from app.models.security_log import SecurityLog, EventType
        from app import db
        import os
        from flask import current_app

        cfg      = current_app.config
        save_dir = cfg.get('SECURITY_FOLDER', 'app/static/images/security')
        os.makedirs(save_dir, exist_ok=True)
        fname    = f"spoof_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        path     = os.path.join(save_dir, fname)
        cv2.imwrite(path, frame)

        log = SecurityLog(
            event_type=EventType.SPOOF_ATTEMPT,
            image_path=path,
            location='Classroom camera',
            description='Anti-spoofing triggered — possible fake face attack',
        )
        db.session.add(log)
        db.session.commit()
        logger.warning(f'Spoof attempt logged: {path}')
    except Exception as e:
        logger.error(f'Spoof log error: {e}')
