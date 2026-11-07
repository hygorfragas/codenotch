import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import smartphone_record_decision  # noqa: E402
from sse_server import LatestFrame  # noqa: E402


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
