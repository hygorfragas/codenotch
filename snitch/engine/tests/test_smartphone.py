import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer  # noqa: E402


class _Names:
    names = {0: "person", 1: "glasses", 2: "ear-mufs", 3: "hands"}


def _analyzer(**kwargs) -> StreamAnalyzer:
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(mock=True, **kwargs))
    analyzer._model = _Names()
    return analyzer


def _detections(boxes, classes, confidences, tracker_id=None):
    import supervision as sv

    return sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        class_id=np.array(classes, dtype=int),
        confidence=np.array(confidences, dtype=np.float32),
        tracker_id=None if tracker_id is None else np.array(tracker_id, dtype=int),
    )


def test_ear_protection_needs_a_higher_confidence_than_glasses():
    analyzer = _analyzer()
    detections = _detections(
        [[10, 10, 200, 400], [40, 40, 90, 70], [50, 80, 80, 110]],
        [0, 1, 2],
        [0.8, 0.12, 0.2],
    )
    kept = analyzer._filter_by_class_confidence(detections)
    labels = [analyzer._class_label(int(class_id)) for class_id in kept.class_id]
    assert labels == ["person", "goggles"]

    strong_ear = _detections(
        [[10, 10, 200, 400], [50, 80, 80, 110]],
        [0, 2],
        [0.8, 0.4],
    )
    kept = analyzer._filter_by_class_confidence(strong_ear)
    assert "ear_protection" in [analyzer._class_label(int(class_id)) for class_id in kept.class_id]


def test_glasses_zoom_runs_only_when_required_and_missing():
    analyzer = _analyzer(required_ppe=("helmet",))
    analyzer._frame_index = 0
    assert analyzer._should_zoom_for_glasses(set()) is False
    analyzer.config.required_ppe = ("goggles",)
    assert analyzer._should_zoom_for_glasses(set()) is True
    assert analyzer._should_zoom_for_glasses({"goggles"}) is False
    analyzer._frame_index = 1
    assert analyzer._should_zoom_for_glasses(set()) is False


def test_phone_hold_keeps_the_timer_for_a_short_gap():
    analyzer = _analyzer()
    analyzer._smartphone = {"enabled": True, "max_continuous_seconds": 10, "hand_limit_seconds": 10}
    people = _detections([[0, 0, 180, 320]], [0], [0.9], tracker_id=[1])
    first = analyzer._observe_smartphones(people, [[40, 140, 90, 210]], None, now=100.0)
    assert first[0]["active"] is True
    assert first[0]["seconds"] == 0
    held = analyzer._observe_smartphones(people, [], None, now=101.0)
    assert held[0]["seconds"] == 1
    assert held[0]["exceeded"] is False
    gone = analyzer._observe_smartphones(people, [], None, now=103.0)
    assert gone == []


def test_phone_episode_posts_after_the_configured_limit(monkeypatch):
    posts = []
    monkeypatch.setenv("SNITCH_WEB_URL", "http://panel.test")
    monkeypatch.setenv("SNITCH_EPISODE_SYNC", "1")
    monkeypatch.setattr("analyze_stream._post_json", lambda url, payload: posts.append((url, payload)))
    analyzer = _analyzer()
    analyzer._smartphone = {"enabled": True, "max_continuous_seconds": 15, "hand_limit_seconds": 15}
    frame = np.zeros((16, 16, 3), dtype=np.uint8)
    analyzer._maybe_record_episode(frame, {
        "smartphones": [{
            "tracker_id": 1,
            "active": True,
            "seconds": 16,
            "limit": 15,
            "exceeded": True,
            "employee_id": None,
        }],
    })
    assert posts[0][0].endswith("/snitch/episodes/smartphone")
    assert posts[0][1]["enabled"] is True
    assert posts[0][1]["limit_exceeded"] is True
    assert posts[0][1]["smartphone_seconds"] == 16
    assert posts[0][1]["max_continuous_seconds"] == 15
