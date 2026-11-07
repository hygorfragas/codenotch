import sys
import time
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


def _analyzer():
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(mock=True, required_ppe=("goggles",)))
    calls: list[int] = []
    analyzer._infer_crop = lambda frame, anchor: calls.append(1) or []
    return analyzer, calls


def test_remembered_glasses_do_not_launch_another_zoom():
    analyzer, calls = _analyzer()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    anchor = np.array([40, 20, 120, 80], dtype=np.float32)
    analyzer._remember_ppe(1, "goggles", np.array([50, 30, 90, 50], np.float32), anchor, 6, time.time())
    updated = analyzer._refine_facial_ppe(frame, _people(1), analyzer._empty_detections())
    assert calls == []
    labels = [analyzer._class_label(int(class_id)) for class_id in updated.class_id]
    assert "goggles" in labels


def test_a_new_tracker_id_does_not_zoom_again_inside_the_interval():
    analyzer, calls = _analyzer()
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    analyzer._roi_at[-1] = 0.0
    analyzer._refine_facial_ppe(frame, _people(1), analyzer._empty_detections())
    assert len(calls) == 1
    calls.clear()
    analyzer._refine_facial_ppe(frame, _people(9), analyzer._empty_detections())
    assert calls == []
