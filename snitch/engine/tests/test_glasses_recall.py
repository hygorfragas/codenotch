import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer, layout_detection_labels  # noqa: E402


class _Names:
    names = {0: "person", 1: "glasses", 2: "head"}


def _analyzer() -> StreamAnalyzer:
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(mock=True, required_ppe=("goggles", "helmet")))
    analyzer._model = _Names()
    return analyzer


def _detections(boxes, classes, confidences):
    import supervision as sv

    return sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        class_id=np.array(classes, dtype=int),
        confidence=np.array(confidences, dtype=np.float32),
    )


def test_low_confidence_glasses_stay_when_inside_a_person():
    analyzer = _analyzer()
    detections = _detections(
        [[10, 10, 200, 400], [40, 40, 90, 70], [400, 10, 460, 40]],
        [0, 1, 1],
        [0.4, 0.12, 0.12],
    )
    kept = analyzer._filter_by_class_confidence(detections)
    labels = [analyzer._class_label(int(class_id)) for class_id in kept.class_id]
    assert labels == ["person", "goggles"]


def test_person_below_strong_threshold_is_dropped():
    analyzer = _analyzer()
    detections = _detections([[10, 10, 80, 80]], [0], [0.2])
    kept = analyzer._filter_by_class_confidence(detections)
    assert len(kept) == 0


def test_glasses_memory_follows_the_head_for_two_seconds():
    analyzer = _analyzer()
    anchor = np.array([100, 40, 180, 120], dtype=np.float32)
    glasses = np.array([120, 70, 160, 90], dtype=np.float32)
    analyzer._remember_ppe(1, "goggles", glasses, anchor, class_id=1, now=10.0)
    moved = np.array([110, 50, 190, 130], dtype=np.float32)
    recalled = analyzer._recall_ppe(1, "goggles", moved, now=12.0)
    assert recalled is not None
    box, class_id = recalled
    assert class_id == 1
    assert box[0] > 110
    assert analyzer._recall_ppe(1, "goggles", moved, now=12.3) is None


def test_overlapping_labels_move_the_smaller_box():
    person = ("[#1] Pessoa · falta Óculos de proteção, Capacete", 8, 8, (255, 255, 255), (8, 30, 220, 400))
    head = ("Cabeça", 40, 8, (255, 255, 255), (40, 30, 100, 90))
    placed = layout_detection_labels([person, head])
    person_origin = placed[0]
    head_origin = placed[1]
    assert person_origin[1:3] == (8, 8)
    assert head_origin[1:3] != (40, 8)
