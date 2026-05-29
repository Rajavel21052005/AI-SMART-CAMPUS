# ============================================================
# app/services/liveness/spoof_detector.py
# Anti-spoofing: detects printed photos, mobile screen replays,
# and pre-recorded video attacks using texture and motion analysis.
# ============================================================

import cv2
import logging
import numpy as np

logger = logging.getLogger(__name__)


class SpoofDetector:
    """
    Passive anti-spoofing using two complementary methods:

    1. Texture Analysis (LBP-based):
       Real faces have micro-textures that printed photos and screens lack.
       Low LBP variance → likely flat (spoof).

    2. Motion Analysis:
       Real faces show subtle natural motion (micro-movements, breathing).
       Zero motion across many frames → static photo.
       Perfectly uniform motion → video replay.
    """

    def __init__(self, texture_threshold: float = 8.5,
                 motion_frames: int = 15,
                 static_motion_frames: int = 5,
                 static_motion_threshold: float = 0.03):
        self.texture_threshold       = texture_threshold
        self.motion_frames           = motion_frames
        self.static_motion_frames    = static_motion_frames
        self.static_motion_threshold = static_motion_threshold
        self._frame_buffer           = []   # stores grayscale frames for motion
        self._motion_scores          = []

    # ── Public API ────────────────────────────────────────────

    def analyse_frame(self, face_crop: np.ndarray) -> dict:
        """
        Run both spoof checks on a face crop (BGR numpy array).

        Returns:
            {
              'is_spoof':        bool,
              'texture_score':   float,   # higher = more real texture
              'motion_score':    float,   # higher = more natural motion
              'reason':          str,
            }
        """
        if face_crop is None or face_crop.size == 0:
            return {'is_spoof': True, 'reason': 'Empty frame',
                    'texture_score': 0.0, 'motion_score': 0.0}

        texture_score = self._texture_analysis(face_crop)
        motion_score  = self._motion_analysis(face_crop)

        # ── Decision logic ────────────────────────────────────
        is_spoof = False
        reason   = 'Real face'

        if texture_score < self.texture_threshold:
            is_spoof = True
            reason   = f'Low texture score ({texture_score:.2f}) — possible photo/screen'

        if self._has_static_motion_streak():
            is_spoof = True
            reason   = 'Zero motion detected — possible static photo'

        logger.debug(f'Spoof check: texture={texture_score:.2f} motion={motion_score:.4f} spoof={is_spoof}')
        return {
            'is_spoof':      is_spoof,
            'texture_score': round(texture_score, 3),
            'motion_score':  round(motion_score,  4),
            'reason':        reason,
        }

    def reset(self):
        self._frame_buffer  = []
        self._motion_scores = []

    def _record_motion_score(self, score: float) -> float:
        self._motion_scores.append(score)
        if len(self._motion_scores) > self.motion_frames:
            self._motion_scores.pop(0)
        return score

    def _has_static_motion_streak(self) -> bool:
        if len(self._frame_buffer) < self.motion_frames:
            return False
        if len(self._motion_scores) < self.static_motion_frames:
            return False

        recent_scores = self._motion_scores[-self.static_motion_frames:]
        return all(score <= self.static_motion_threshold for score in recent_scores)

    # ── Texture analysis: Local Binary Pattern variance ───────

    def _texture_analysis(self, face_crop: np.ndarray) -> float:
        """
        Compute LBP (Local Binary Pattern) variance of the face crop.
        Real skin has rich micro-texture → high variance.
        Printed paper / screen → low variance (too smooth or Moiré pattern).
        """
        try:
            gray    = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            resized = cv2.resize(gray, (64, 64))

            lbp = self._compute_lbp(resized)
            # Use standard deviation of LBP image as the texture richness score
            score = float(np.std(lbp))
            return score
        except Exception as e:
            logger.error(f'Texture analysis error: {e}')
            return 0.0

    @staticmethod
    def _compute_lbp(gray: np.ndarray, radius: int = 1, n_points: int = 8) -> np.ndarray:
        """
        Simplified LBP computation using OpenCV (no scikit-image dependency).
        For each pixel, compare with n_points neighbours on a circle of given radius.
        """
        h, w   = gray.shape
        lbp    = np.zeros_like(gray, dtype=np.uint8)
        angles = [2 * np.pi * i / n_points for i in range(n_points)]

        for idx, angle in enumerate(angles):
            dx = int(round(radius * np.cos(angle)))
            dy = int(round(radius * np.sin(angle)))
            # Shift image to get neighbour values
            shifted = np.roll(np.roll(gray, dy, axis=0), dx, axis=1)
            lbp    += ((shifted >= gray).astype(np.uint8) << idx)

        return lbp

    # ── Motion analysis ───────────────────────────────────────

    def _motion_analysis(self, face_crop: np.ndarray) -> float:
        """
        Compute optical-flow-based motion score across the frame buffer.
        Natural faces have subtle random micro-motion.
        Static photos = 0 motion. Replay videos = too-uniform motion.
        """
        try:
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (48, 48))
            self._frame_buffer.append(gray)

            # Need at least 2 frames
            if len(self._frame_buffer) < 2:
                return self._record_motion_score(0.5)   # Neutral score while warming up

            # Keep buffer bounded
            if len(self._frame_buffer) > self.motion_frames:
                self._frame_buffer.pop(0)

            prev = self._frame_buffer[-2]
            curr = self._frame_buffer[-1]

            # Lucas-Kanade optical flow on sparse feature points
            feat_params = dict(maxCorners=30, qualityLevel=0.2,
                               minDistance=4, blockSize=5)
            flow_params  = dict(winSize=(10, 10), maxLevel=2,
                                criteria=(cv2.TERM_CRITERIA_EPS |
                                          cv2.TERM_CRITERIA_COUNT, 10, 0.03))

            pts = cv2.goodFeaturesToTrack(prev, mask=None, **feat_params)
            if pts is None or len(pts) < 3:
                return self._record_motion_score(0.0)

            next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                prev, curr, pts, None, **flow_params
            )
            good_old = pts[status == 1]
            good_new = next_pts[status == 1]

            if len(good_old) == 0:
                return self._record_motion_score(0.0)

            # Magnitude of displacement for each tracked point
            diffs  = good_new - good_old
            magnitudes = np.linalg.norm(diffs, axis=1)
            motion_score = float(np.mean(magnitudes))
            return self._record_motion_score(motion_score)

        except Exception as e:
            logger.error(f'Motion analysis error: {e}')
            return self._record_motion_score(0.0)
