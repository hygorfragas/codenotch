import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from phone_watch import PhoneClock, PhoneSighting, phone_near_body  # noqa: E402


def test_phone_on_the_hand_counts_and_a_phone_on_the_chair_does_not():
    hand = np.array([100, 200, 160, 280], dtype=np.float32)
    face = np.array([80, 40, 150, 120], dtype=np.float32)
    head = np.array([70, 20, 170, 150], dtype=np.float32)
    on_hand = np.array([110, 210, 150, 260], dtype=np.float32)
    on_chair = np.array([400, 300, 460, 380], dtype=np.float32)
    assert phone_near_body(on_hand, [hand], [face], [head]) == "hand"
    assert phone_near_body(on_chair, [hand], [face], [head]) is None


def test_confirmed_use_reaches_the_limit_and_an_id_change_keeps_the_clock():
    clock = PhoneClock(grace_seconds=10.0, reid_pixels=220.0, max_gap=20.0)
    first = clock.update([PhoneSighting(1, (10.0, 10.0), True, True)], now=10.0, limit=30)
    assert first[0]["elapsed_s"] == 0
    assert first[0]["limit_exceeded"] is False
    second = clock.update([PhoneSighting(1, (12.0, 10.0), True, True)], now=20.0, limit=30)
    assert second[0]["elapsed_s"] == 10
    moved = clock.update([PhoneSighting(9, (18.0, 12.0), True, True)], now=25.0, limit=30)
    assert moved[0]["tracker_id"] == 9
    assert moved[0]["elapsed_s"] == 15
    done = clock.update([PhoneSighting(9, (18.0, 12.0), True, True)], now=41.0, limit=30)
    assert done[0]["elapsed_s"] >= 30
    assert done[0]["limit_exceeded"] is True
    again = clock.update([PhoneSighting(9, (18.0, 12.0), True, True)], now=42.0, limit=30)
    assert again[0]["limit_exceeded"] is False


def test_earplug_training_script_does_not_train():
    import subprocess

    script = ROOT / "scripts" / "train_earplug.py"
    result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Treino não iniciado" in result.stdout


def test_a_visible_phone_does_not_count_until_use_is_confirmed():
    clock = PhoneClock()
    clock.update([PhoneSighting(1, (0.0, 0.0), True, False)], now=5.0, limit=30)
    later = clock.update([PhoneSighting(1, (0.0, 0.0), True, False)], now=15.0, limit=30)
    assert later[0]["elapsed_s"] == 0
