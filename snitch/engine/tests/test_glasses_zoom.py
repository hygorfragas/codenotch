import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer  # noqa: E402


def _people(tracker_id: int):
    import supervision as sv

    return sv.Detections(
        xyxy=np.array([[10, 10, 200, 400]], dtype=np.float32),
        class_id=np.array([0]),
        confidence=np.array([0.9], dtype=np.float32),
        tracker_id=np.array([tracker_id]),
    )


def _glasses():
    import supervision as sv

    return sv.Detections(
        xyxy=np.array([[50, 30, 90, 55]], dtype=np.float32),
        class_id=np.array([6]),
        confidence=np.array([0.8], dtype=np.float32),
    )


def _analyzer():
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(mock=True, required_ppe=("goggles",)))
    calls: list[int] = []
    analyzer._infer_crop = lambda frame, anchor: calls.append(1) or []
    return analyzer, calls


def test_one_frame_does_not_confirm_glasses_or_zoom():
    analyzer, calls = _analyzer()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    updated = analyzer._refine_facial_ppe(frame, _people(1), _glasses())
    assert calls == []
    if updated.class_id is None or len(updated) == 0:
        return
    labels = [analyzer._class_label(int(class_id)) for class_id in updated.class_id]
    assert "goggles" not in labels


def test_a_majority_holds_glasses_through_one_miss_without_zoom():
    analyzer, calls = _analyzer()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    people = _people(1)
    glasses = _glasses()
    for _ in range(3):
        analyzer._refine_facial_ppe(frame, people, glasses)
    calls.clear()
    updated = analyzer._refine_facial_ppe(frame, people, analyzer._empty_detections())
    assert calls == []
    labels = [analyzer._class_label(int(class_id)) for class_id in updated.class_id]
    assert "goggles" in labels


def test_a_new_tracker_id_does_not_zoom_again_inside_the_interval():
    analyzer, calls = _analyzer()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    for _ in range(5):
        analyzer._refine_facial_ppe(frame, _people(1), analyzer._empty_detections())
    assert len(calls) == 1
    calls.clear()
    analyzer._refine_facial_ppe(frame, _people(9), analyzer._empty_detections())
    assert calls == []
