import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer  # noqa: E402


class _Names:
    names = {
        0: "person",
        1: "head",
        2: "face",
        3: "hands",
        4: "gloves",
        5: "ear-mufs",
        6: "glasses",
        7: "ear",
    }


def _analyzer() -> StreamAnalyzer:
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(mock=True, required_ppe=("goggles", "gloves")))
    analyzer._model = _Names()
    return analyzer


def _detections(boxes, classes, confidences):
    import supervision as sv

    return sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        class_id=np.array(classes, dtype=int),
        confidence=np.array(confidences, dtype=np.float32),
    )


def _labels(analyzer, detections) -> list[str]:
    if detections.class_id is None or len(detections) == 0:
        return []
    return [analyzer._class_label(int(class_id)) for class_id in detections.class_id]


def test_gloves_off_the_hand_are_dropped():
    analyzer = _analyzer()
    detections = _detections(
        [
            [10, 10, 220, 460],
            [30, 250, 120, 360],
            [40, 270, 100, 340],
            [150, 80, 210, 150],
        ],
        [0, 3, 4, 4],
        [0.9, 0.9, 0.4, 0.9],
    )
    assert _labels(analyzer, analyzer._filter_by_class_confidence(detections)).count("gloves") == 1


def test_overlapping_earmuffs_collapse_to_one_box():
    analyzer = _analyzer()
    detections = _detections(
        [
            [10, 10, 220, 460],
            [40, 30, 140, 150],
            [55, 50, 100, 100],
            [58, 52, 104, 102],
            [60, 48, 102, 98],
        ],
        [0, 1, 5, 5, 5],
        [0.9, 0.9, 0.7, 0.6, 0.5],
    )
    assert _labels(analyzer, analyzer._filter_by_class_confidence(detections)).count("ear_protection") == 1


def test_distant_glasses_need_a_higher_confidence():
    analyzer = _analyzer()
    weak = _detections(
        [[10, 10, 80, 200], [20, 16, 52, 48], [26, 24, 46, 36]],
        [0, 1, 6],
        [0.9, 0.9, 0.2],
    )
    strong = _detections(
        [[10, 10, 80, 200], [20, 16, 52, 48], [26, 24, 46, 36]],
        [0, 1, 6],
        [0.9, 0.9, 0.5],
    )
    assert "goggles" not in _labels(analyzer, analyzer._filter_by_class_confidence(weak))
    assert "goggles" in _labels(analyzer, analyzer._filter_by_class_confidence(strong))
