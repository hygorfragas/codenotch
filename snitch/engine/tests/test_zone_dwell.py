import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import (  # noqa: E402
    AnalyzeStreamConfig,
    StreamAnalyzer,
    ZoneConfig,
    draw_unicode_labels,
    person_intersects_zone,
    resolve_unicode_font_path,
)


def _people(tracker_ids, boxes):
    import supervision as sv

    count = len(tracker_ids)
    return sv.Detections(
        xyxy=np.array(boxes, dtype=np.float32),
        class_id=np.zeros(count, dtype=int),
        confidence=np.ones(count, dtype=np.float32),
        tracker_id=np.array(tracker_ids, dtype=int),
    )


def _analyzer() -> StreamAnalyzer:
    zone = ZoneConfig(
        name="Banheiro",
        polygon=np.array([[20, 40], [600, 40], [600, 400], [20, 400]], dtype=np.float32),
        zone_type="passagem",
        max_dwell_seconds=40,
        zone_id=7,
    )
    return StreamAnalyzer(AnalyzeStreamConfig(mock=True, camera_id=1, zones=[zone]))


def test_unicode_font_is_truetype_and_draws_accents():
    path = resolve_unicode_font_path()
    assert path is not None
    assert Path(path).name in {"DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "Arial.ttf", "Arial Bold.ttf", "Helvetica.ttc"}
    blank = np.zeros((72, 520, 3), dtype=np.uint8)
    cedilla = draw_unicode_labels(blank.copy(), [("Cabeça", 8, 24, (255, 255, 255))])
    marks = draw_unicode_labels(blank.copy(), [("Cabe??a", 8, 24, (255, 255, 255))])
    glasses = draw_unicode_labels(blank.copy(), [("Óculos de proteção", 8, 24, (255, 255, 255))])
    ascii_glasses = draw_unicode_labels(blank.copy(), [("Oculos de protecao", 8, 24, (255, 255, 255))])
    assert not np.array_equal(cedilla, marks)
    assert not np.array_equal(glasses, ascii_glasses)
    assert int(cedilla.sum()) > 0


def test_zone_label_uses_unicode_caption():
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(
        mock=True,
        zones=[ZoneConfig(
            name="Área restrita",
            polygon=np.array([[10, 30], [200, 30], [200, 120], [10, 120]], dtype=np.float32),
            zone_type="restrita",
        )],
    ))
    frame = np.zeros((160, 320, 3), dtype=np.uint8)
    labeled = analyzer._draw_zones(frame.copy(), [{
        "name": "Área restrita",
        "occupied": True,
        "exceeded": False,
        "label": "Área restrita · Restrita · 3s",
    }])
    plain = analyzer._draw_zones(frame.copy(), [{
        "name": "Área restrita",
        "occupied": True,
        "exceeded": False,
        "label": "Area restrita · Restrita · 3s",
    }])
    assert not np.array_equal(labeled, plain)


def test_upper_body_counts_as_inside_when_feet_are_outside():
    polygon = np.array([[0, 0], [640, 0], [640, 220], [0, 220]], dtype=np.float32)
    box = np.array([200, 40, 400, 470], dtype=np.float32)
    assert person_intersects_zone(box, polygon) is True


def test_small_corner_overlap_below_15_percent_stays_outside():
    box = np.array([0, 0, 100, 100], dtype=np.float32)
    strip = np.array([[0, -10], [5, -10], [5, 110], [0, 110]], dtype=np.float32)
    assert person_intersects_zone(box, strip) is False
    wider = np.array([[0, -10], [20, -10], [20, 110], [0, 110]], dtype=np.float32)
    assert person_intersects_zone(box, wider) is True


def test_tracker_flicker_keeps_dwell_inside_the_same_zone():
    analyzer = _analyzer()
    left = [40, 80, 180, 320]
    right = [360, 80, 520, 320]
    _, _, first = analyzer._zone_status(_people([1, 2], [left, right]), 640, 480, now=1000)
    assert first[0]["elapsed_s"] == 0
    assert first[0]["occupied"] is True
    _, exceeded, second = analyzer._zone_status(_people([1, 99], [left, [370, 90, 530, 330]]), 640, 480, now=1004)
    elapsed = sorted(int(1004 - record["started"]) for record in analyzer._occupancy.values())
    assert elapsed == [4, 4]
    assert {record["tracker_id"] for record in analyzer._occupancy.values()} == {1, 99}
    assert exceeded == []
    assert second[0]["label"] == "Banheiro · Passagem · 4s / 40s"
    latest = second
    for moment in range(1008, 1041, 4):
        _, exceeded, latest = analyzer._zone_status(
            _people([1, 99], [left, [370, 90, 530, 330]]),
            640,
            480,
            now=moment,
        )
    assert "Banheiro" in exceeded
    assert latest[0]["exceeded"] is True
    assert latest[0]["elapsed_s"] == 40
    assert latest[0]["label"] == "Banheiro · Passagem · 40s / 40s"


def test_linked_employee_keeps_dwell_when_tracker_id_changes():
    analyzer = _analyzer()
    analyzer._tracker_links = {
        "9": {"employee_id": 4, "name": "Ana"},
        "30": {"employee_id": 4, "name": "Ana"},
    }
    box = [[80, 80, 220, 300]]
    analyzer._zone_status(_people([9], box), 640, 480, now=1000)
    analyzer._zone_status(_people([30], box), 640, 480, now=1010)
    record = analyzer._occupancy[("employee", 4, "Banheiro")]
    assert int(1010 - record["started"]) == 10
    assert record["tracker_id"] == 30


def test_frame_lists_each_missing_required_ppe_item():
    analyzer = StreamAnalyzer(AnalyzeStreamConfig(
        mock=True,
        camera_id=1,
        required_ppe=("helmet", "gloves", "vest"),
    ))
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    _annotated, state = analyzer.process_frame(frame)
    assert state["required_ppe"] == ["helmet", "gloves", "vest"]
    assert state["missing_ppe_items"] == ["helmet", "gloves", "vest"]
    assert state["missing_ppe_labels_pt"] == ["Capacete", "Luvas", "Colete refletivo"]
    assert state["persons"][0]["missing_ppe_items"] == ["helmet", "gloves", "vest"]

    import supervision as sv

    people = sv.Detections(
        xyxy=np.array([[0, 0, 100, 100]], dtype=np.float32),
        class_id=np.array([0]),
        confidence=np.array([0.9]),
        tracker_id=np.array([3]),
    )
    helmet = sv.Detections(
        xyxy=np.array([[10, 10, 40, 40]], dtype=np.float32),
        class_id=np.array([5]),
        confidence=np.array([0.9]),
    )
    persons = analyzer._persons_from_tracks(people, {}, helmet)
    partial = {
        "persons": [{
            "tracker_id": 3,
            "ppe_missing": persons[0].ppe_missing,
            "ppe_detected": persons[0].ppe_detected,
        }],
    }
    analyzer._attach_missing_ppe(partial)
    assert partial["missing_ppe_items"] == ["gloves", "vest"]
    assert partial["missing_ppe_labels_pt"] == ["Luvas", "Colete refletivo"]


def test_idle_zone_posts_without_waiting_for_missing_ppe(monkeypatch):
    posts: list[tuple[str, dict]] = []
    monkeypatch.setenv("SNITCH_WEB_URL", "http://panel.test")
    monkeypatch.setenv("SNITCH_EPISODE_SYNC", "1")
    monkeypatch.setenv("SNITCH_LOCATION_ID", "2")
    monkeypatch.setattr("analyze_stream._post_json", lambda url, payload: posts.append((url, payload)))
    analyzer = _analyzer()
    frame = np.zeros((32, 32, 3), dtype=np.uint8)
    waiting = {
        "persons": [{"tracker_id": 9}],
        "zone_dwell": [{
            "name": "Banheiro",
            "zone_id": 7,
            "type": "passagem",
            "max_dwell_seconds": 40,
            "elapsed_s": 14,
            "occupied": True,
            "present": True,
            "exceeded": False,
            "tracker_id": 9,
            "employee_id": None,
        }],
    }
    analyzer._maybe_record_episode(frame, waiting)
    assert posts == []

    ready = {
        "jev": {"any_missing_required_ppe": True, "any_person_in_restricted_zone": False},
        "persons": [{
            "tracker_id": 9,
            "ppe_detected": ["boots"],
            "ppe_missing": ["helmet", "gloves", "vest"],
            "missing_ppe_items": ["helmet", "gloves", "vest"],
            "missing_ppe_labels_pt": ["Capacete", "Luvas", "Colete refletivo"],
        }],
        "zone_dwell": [{
            "name": "Banheiro",
            "zone_id": 7,
            "type": "passagem",
            "max_dwell_seconds": 40,
            "elapsed_s": 41,
            "occupied": True,
            "present": True,
            "exceeded": True,
            "tracker_id": 9,
            "employee_id": 4,
        }],
    }
    analyzer._maybe_record_episode(frame, ready)
    urls = [url for url, _payload in posts]
    assert "http://panel.test/snitch/episodes/ppe" in urls
    assert "http://panel.test/snitch/episodes/idle-zone" in urls
    zone = next(payload for url, payload in posts if url.endswith("/idle-zone"))
    assert zone["zone"] == "Banheiro"
    assert zone["zone_id"] == 7
    assert zone["camera_id"] == 1
    assert zone["tracker_id"] == 9
    assert zone["employee_id"] == 4
    assert zone["dwell_seconds"] == 41
    assert zone["photo"].startswith("data:image/jpeg;base64,")
    ppe = next(payload for url, payload in posts if url.endswith("/ppe"))
    assert ppe["missing_ppe"] == ["helmet", "gloves", "vest"]
    assert ppe["missing_ppe_labels_pt"] == ["Capacete", "Luvas", "Colete refletivo"]
    assert ppe["detected_ppe"] == ["boots"]

    analyzer._maybe_record_episode(frame, ready)
    assert len(posts) == 2

    restricted = {
        "zone_dwell": [{
            "name": "Área restrita",
            "zone_id": 8,
            "type": "restrita",
            "max_dwell_seconds": None,
            "elapsed_s": 2,
            "occupied": True,
            "present": True,
            "exceeded": False,
            "tracker_id": 9,
            "employee_id": None,
        }],
    }
    analyzer._maybe_record_episode(frame, restricted)
    assert len(posts) == 3
    assert posts[-1][1]["zone_type"] == "restrita"
