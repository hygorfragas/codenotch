import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jev_image import JevImageClient, fit_bgr, noul_is_true  # noqa: E402


def test_small_crop_is_raised_to_the_minimum_the_api_accepts():
    fitted = fit_bgr(np.full((80, 100, 3), 20, dtype=np.uint8))
    height, width = fitted.shape[:2]
    assert min(height, width) >= 280
    assert max(height, width) <= 1568
    assert height * width >= 78_400


def test_wide_photo_is_capped_and_padded_instead_of_being_rejected():
    fitted = fit_bgr(np.full((200, 4000, 3), 20, dtype=np.uint8))
    height, width = fitted.shape[:2]
    assert 280 <= height <= 1568
    assert 280 <= width <= 1568


def test_the_same_jpeg_is_not_charged_twice_and_the_ceiling_stops_the_next_one(tmp_path):
    calls = []

    def transport(jpeg, questions):
        calls.append(jpeg)
        return 200, {"answers": {"solid": {"type": "noul", "noul": 0.9}}, "usage": {"images": 1}}, 10.0

    client = JevImageClient(cache_dir=tmp_path, ceiling_usd=0.00015, price_usd=0.0001, transport=transport)
    first = client.ask_jpeg(b"same-image", {"solid": "Is it flat?"})
    second = client.ask_jpeg(b"same-image", {"solid": "Is it flat?"})
    blocked = client.ask_jpeg(b"other-image", {"solid": "Is it flat?"})
    assert first["charged"] is True and first["cache"] is False
    assert second["charged"] is False and second["cache"] is True
    assert blocked["status"] == "teto"
    assert len(calls) == 1
    assert client.ledger["images_sent"] == 1
    assert noul_is_true(first["answers"]["solid"]) is True


def test_the_default_client_does_not_stop_at_a_spending_ceiling(tmp_path):
    calls = []

    def transport(jpeg, questions):
        calls.append(jpeg)
        return 200, {"answers": {"solid": {"type": "noul", "noul": 0.2}}, "usage": {}}, 1.0

    client = JevImageClient(cache_dir=tmp_path, transport=transport)
    assert client.ceiling_usd is None
    assert client.ask_jpeg(b"one", {"solid": "q"})["charged"] is True
    assert client.ask_jpeg(b"two", {"solid": "q"})["charged"] is True
    assert len(calls) == 2


def test_a_failed_key_does_not_spend_the_budget(tmp_path):
    def transport(jpeg, questions):
        return 401, {"error": "unauthorized"}, 5.0

    client = JevImageClient(cache_dir=tmp_path, transport=transport)
    result = client.ask_jpeg(b"image", {"solid": "Is it flat?"})
    assert result["status"] == 401
    assert result["charged"] is False
    assert client.ledger["images_sent"] == 0
    assert noul_is_true({"noul": 0.49}) is False
