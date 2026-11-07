import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import map_boxes_to_frame, smartphone_record_decision  # noqa: E402
from sse_server import LatestFrame  # noqa: E402


def test_crop_box_keeps_its_place_when_the_crop_is_not_at_the_origin():
    mapped = map_boxes_to_frame(
        [[10, 20, 30, 40]],
        (180, 90),
        (400, 100),
        (180, 90),
        (1080, 1920),
    )
    assert mapped == [[410.0, 120.0, 430.0, 140.0]]
    clipped = map_boxes_to_frame(
        [[0, 0, 90, 180]],
        (180, 90),
        (1900, 1000),
        (180, 90),
        (1080, 1920),
    )
    assert clipped[0][2] == 1920.0
    assert clipped[0][3] == 1080.0


def test_latest_frame_keeps_only_the_newest():
    slot = LatestFrame()
    first = slot.publish("antigo")
    second = slot.publish("novo")
    third = slot.publish("atual")
    snap = slot.latest()
    assert first < second < third
    assert snap is not None
    assert snap[0] == third
    assert snap[1] == "atual"


def test_smartphone_record_needs_laya_or_a_slow_fallback():
    assert smartphone_record_decision(
        enabled=True, seconds=16, limit=15, laya_confirmed=True, laya_available=True,
    ) == (True, "laya")
    assert smartphone_record_decision(
        enabled=True, seconds=16, limit=15, laya_confirmed=False, laya_available=True,
    ) == (False, "laya_nao_confirmou")
    assert smartphone_record_decision(
        enabled=True, seconds=16, limit=15, laya_confirmed=None, laya_available=False,
    ) == (False, "laya_indisponivel")
    assert smartphone_record_decision(
        enabled=True, seconds=20, limit=15, laya_confirmed=None, laya_available=False,
    ) == (True, "fallback_local")
