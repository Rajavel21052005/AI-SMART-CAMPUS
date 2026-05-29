# ============================================================
# app/services/liveness/liveness_detector.py
# Anti-spoofing: blink detection, head-movement challenge,
# motion analysis — prevents photo/screen/video replay attacks.
# Uses MediaPipe Face Mesh (468 landmarks, no GPU required).
# ============================================================

import cv2
import logging
import numpy as np
import time
import random
from enum import Enum

logger = logging.getLogger(__name__)

# ── MediaPipe landmark indices ────────────────────────────────
# Eye landmarks for EAR (Eye Aspect Ratio) blink detection
LEFT_EYE  = [362, 385, 387, 263, 373, 380]   # left eye contour
RIGHT_EYE = [33,  160, 158, 133, 153, 144]   # right eye contour

# Nose tip and chin for head-pose estimation
NOSE_TIP  = 1
CHIN      = 152
LEFT_EAR  = 234
RIGHT_EAR = 454
LEFT_EYE_INNER  = 362
RIGHT_EYE_INNER = 133

# EAR threshold below which an eye is considered closed
EAR_BLINK_THRESHOLD = 0.22

# Challenge types
class Challenge(Enum):
    BLINK       = 'blink'
    TURN_LEFT   = 'turn_left'
    TURN_RIGHT  = 'turn_right'
    NOD         = 'nod'


class LivenessDetector:
    """
    Stateful liveness detector for a single face-recognition session.

    Usage:
        det = LivenessDetector()
        while capturing:
            result = det.process_frame(frame)
            if result['verified']:
                # liveness confirmed — proceed with recognition
    """

    def __init__(self, required_blinks: int = 2, challenge_timeout: float = 8.0):
        self.required_blinks   = required_blinks
        self.challenge_timeout = challenge_timeout

        # State
        self.blink_count       = 0
        self.ear_buffer        = []          # rolling EAR values
        self.eye_was_closed    = False
        self.verified          = False
        self.failed            = False
        self.start_time        = time.time()
        self.message           = 'Please look at the camera…'

        # Active challenge
        self.current_challenge = self._pick_challenge()
        self.challenge_met     = False
        self.challenge_start   = time.time()

        # Head-pose tracking
        self._prev_yaw   = None
        self._prev_pitch = None

        # MediaPipe
        self._mp_face_mesh = None
        self._face_mesh    = None
        self._init_mediapipe()

    def _init_mediapipe(self):
        """Lazy-load MediaPipe to avoid import cost at module level."""
        try:
            import mediapipe as mp
            self._mp_face_mesh = mp.solutions.face_mesh
            self._face_mesh    = self._mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            )
            logger.info('MediaPipe FaceMesh initialised')
        except ImportError:
            logger.error('mediapipe not installed — liveness detection disabled')
            self._face_mesh = None

    # ── Main processing method ────────────────────────────────

    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Process a single BGR frame.

        Returns dict:
          {
            'verified':  bool,   # True = liveness confirmed
            'failed':    bool,   # True = timeout / spoof detected
            'blinks':    int,
            'message':   str,    # Instruction to show user
            'challenge': str,    # Current challenge name
            'ear':       float,  # Current eye aspect ratio
          }
        """
        if self.verified:
            return self._result(verified=True)
        if self.failed:
            return self._result(failed=True)

        # Timeout check
        elapsed = time.time() - self.start_time
        if elapsed > self.challenge_timeout * 2:
            self.failed  = True
            self.message = 'Liveness timeout — please try again.'
            return self._result(failed=True)

        if self._face_mesh is None:
            # MediaPipe unavailable — pass-through (no liveness)
            self.verified = True
            self.message  = 'Liveness check bypassed (mediapipe missing).'
            return self._result(verified=True)

        # Convert to RGB for MediaPipe
        rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(rgb)

        if not result.multi_face_landmarks:
            self.message = 'No face detected — move closer.'
            return self._result()

        landmarks = result.multi_face_landmarks[0].landmark
        h, w, _   = frame.shape

        # ── Step 1: Blink detection ───────────────────────────
        ear = self._compute_ear(landmarks, w, h)
        self.ear_buffer.append(ear)
        if len(self.ear_buffer) > 5:
            self.ear_buffer.pop(0)

        avg_ear = np.mean(self.ear_buffer)
        if avg_ear < EAR_BLINK_THRESHOLD:
            if not self.eye_was_closed:
                self.eye_was_closed = True
        else:
            if self.eye_was_closed:
                self.blink_count    += 1
                self.eye_was_closed  = False
                logger.debug(f'Blink detected: total={self.blink_count}')

        # ── Step 2: Head-pose challenge ───────────────────────
        yaw, pitch = self._compute_head_pose(landmarks, w, h)
        self._evaluate_challenge(yaw, pitch)

        # ── Step 3: Check completion ──────────────────────────
        if self.blink_count >= self.required_blinks and self.challenge_met:
            self.verified = True
            self.message  = '✅  Liveness verified!'
            return self._result(verified=True)

        # Build user instruction
        if self.blink_count < self.required_blinks:
            remaining     = self.required_blinks - self.blink_count
            self.message  = f'Please blink {remaining} more time(s)…'
        elif not self.challenge_met:
            self.message  = self._challenge_instruction()

        return self._result(ear=avg_ear)

    # ── EAR computation ───────────────────────────────────────

    def _compute_ear(self, landmarks, w: int, h: int) -> float:
        """
        Eye Aspect Ratio (EAR) = ||p2-p6|| + ||p3-p5|| / (2 * ||p1-p4||)
        EAR < threshold → eye closed → blink.
        """
        def pt(idx):
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])

        # Left eye
        l_ear = self._ear_for_eye([pt(i) for i in LEFT_EYE])
        # Right eye
        r_ear = self._ear_for_eye([pt(i) for i in RIGHT_EYE])
        return (l_ear + r_ear) / 2.0

    @staticmethod
    def _ear_for_eye(pts: list) -> float:
        """Compute EAR for one eye given 6 landmark points."""
        A = np.linalg.norm(pts[1] - pts[5])
        B = np.linalg.norm(pts[2] - pts[4])
        C = np.linalg.norm(pts[0] - pts[3])
        if C == 0:
            return 0.0
        return (A + B) / (2.0 * C)

    # ── Head-pose estimation ──────────────────────────────────

    def _compute_head_pose(self, landmarks, w: int, h: int) -> tuple[float, float]:
        """
        Approximate yaw (left-right) and pitch (up-down) from 2D landmarks.
        Returns (yaw_degrees, pitch_degrees).
        """
        def lm(idx):
            p = landmarks[idx]
            return np.array([p.x * w, p.y * h])

        nose     = lm(NOSE_TIP)
        chin_pt  = lm(CHIN)
        left_e   = lm(LEFT_EAR)
        right_e  = lm(RIGHT_EAR)

        # Yaw: horizontal imbalance between ears and nose
        face_width = np.linalg.norm(left_e - right_e)
        if face_width == 0:
            return 0.0, 0.0
        nose_offset = nose[0] - (left_e[0] + right_e[0]) / 2
        yaw         = (nose_offset / face_width) * 90.0   # approx degrees

        # Pitch: vertical position of nose relative to chin
        face_height  = np.linalg.norm(chin_pt - lm(NOSE_TIP))
        mid_y        = (lm(LEFT_EYE_INNER)[1] + lm(RIGHT_EYE_INNER)[1]) / 2
        vertical_pos = nose[1] - mid_y
        pitch        = (vertical_pos / max(face_height, 1)) * 90.0

        return float(yaw), float(pitch)

    def _evaluate_challenge(self, yaw: float, pitch: float):
        """Check if the head-pose matches the current challenge."""
        ch = self.current_challenge

        # Timeout this challenge and mark failed if exceeded
        elapsed = time.time() - self.challenge_start
        if elapsed > self.challenge_timeout:
            self.failed  = True
            self.message = f'Challenge timed out. Please retry.'
            return

        if ch == Challenge.TURN_LEFT  and yaw < -18:
            self.challenge_met = True
        elif ch == Challenge.TURN_RIGHT and yaw > 18:
            self.challenge_met = True
        elif ch == Challenge.NOD       and pitch > 15:
            self.challenge_met = True
        elif ch == Challenge.BLINK:
            # Blink challenge — handled by blink counter
            if self.blink_count >= self.required_blinks:
                self.challenge_met = True

    def _challenge_instruction(self) -> str:
        instructions = {
            Challenge.TURN_LEFT:  '⬅️  Please turn your head LEFT',
            Challenge.TURN_RIGHT: '➡️  Please turn your head RIGHT',
            Challenge.NOD:        '⬇️  Please nod your head DOWN',
            Challenge.BLINK:      '👁  Please blink naturally',
        }
        return instructions.get(self.current_challenge, 'Follow the instruction on screen')

    @staticmethod
    def _pick_challenge() -> Challenge:
        """Randomly pick one head-movement challenge."""
        return random.choice([Challenge.TURN_LEFT, Challenge.TURN_RIGHT, Challenge.NOD])

    def _result(self, verified=False, failed=False, ear=0.0) -> dict:
        return {
            'verified':  self.verified or verified,
            'failed':    self.failed   or failed,
            'blinks':    self.blink_count,
            'message':   self.message,
            'challenge': self.current_challenge.value,
            'ear':       round(ear, 4),
        }

    def reset(self):
        """Reset detector state for a new session."""
        self.__init__(self.required_blinks, self.challenge_timeout)
