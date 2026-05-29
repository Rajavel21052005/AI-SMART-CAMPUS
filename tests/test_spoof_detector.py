import numpy as np

from app.services.liveness.spoof_detector import SpoofDetector


def test_single_zero_motion_frame_does_not_mark_spoof(monkeypatch):
    detector = SpoofDetector(motion_frames=15, static_motion_frames=5)
    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    detector._frame_buffer = [np.zeros((48, 48), dtype=np.uint8)] * 15
    detector._motion_scores = [0.4, 0.8, 0.6, 0.9, 0.0]

    monkeypatch.setattr(detector, '_texture_analysis', lambda _: 92.0)
    monkeypatch.setattr(detector, '_motion_analysis', lambda _: 0.0)

    result = detector.analyse_frame(frame)

    assert result['is_spoof'] is False


def test_sustained_zero_motion_marks_spoof(monkeypatch):
    detector = SpoofDetector(motion_frames=15, static_motion_frames=5)
    frame = np.zeros((64, 64, 3), dtype=np.uint8)

    detector._frame_buffer = [np.zeros((48, 48), dtype=np.uint8)] * 15
    detector._motion_scores = [0.4, 0.8, 0.6, 0.9, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0]

    monkeypatch.setattr(detector, '_texture_analysis', lambda _: 92.0)
    monkeypatch.setattr(detector, '_motion_analysis', lambda _: 0.0)

    result = detector.analyse_frame(frame)

    assert result['is_spoof'] is True
