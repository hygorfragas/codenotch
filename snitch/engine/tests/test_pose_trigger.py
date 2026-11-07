import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pose_read import phone_pose_trigger  # noqa: E402


def test_a_hand_at_the_ear_or_a_lowered_head_asks_for_the_phone_crop():
    near_ear = {
        "nose": (100.0, 80.0),
        "eyes": [(90.0, 70.0), (110.0, 70.0)],
        "ears": [(80.0, 80.0)],
        "wrists": [(82.0, 84.0)],
    }
    lowered = {
        "nose": (100.0, 120.0),
        "eyes": [(90.0, 70.0), (110.0, 70.0)],
        "ears": [],
        "wrists": [(20.0, 200.0)],
    }
    away = {
        "nose": (100.0, 80.0),
        "eyes": [(90.0, 70.0), (110.0, 70.0)],
        "ears": [(80.0, 80.0)],
        "wrists": [(400.0, 400.0)],
    }
    assert phone_pose_trigger(near_ear, 100.0) is True
    assert phone_pose_trigger(lowered, 100.0) is True
    assert phone_pose_trigger(away, 100.0) is False
