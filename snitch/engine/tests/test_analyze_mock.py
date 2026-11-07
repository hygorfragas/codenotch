import os

import numpy as np

# Garante import do pacote engine
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer, canonical_class_name  # noqa: E402


def test_process_frame_mock_returns_state_and_image():
    config = AnalyzeStreamConfig(mock=True, camera_id=99)
    analyzer = StreamAnalyzer(config)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    annotated, state = analyzer.process_frame(frame)
    assert annotated.shape == frame.shape
    assert state["camera_id"] == 99
    assert "persons" in state


def test_official_sh17_aliases_match_required_ppe():
    assert canonical_class_name("safety-vest") == "vest"
    assert canonical_class_name("shoes") == "boots"
    assert canonical_class_name("glasses") == "goggles"
    assert canonical_class_name("ear-mufs") == "ear_protection"
    assert canonical_class_name("face-mask") == "mask"
    assert canonical_class_name("hands") == "hand"
    assert canonical_class_name("helmet") == "helmet"


def test_real_model_names_are_canonicalized():
    config = AnalyzeStreamConfig(mock=True, camera_id=1)
    analyzer = StreamAnalyzer(config)

    class _Model:
        names = {
            0: "person",
            9: "gloves",
            10: "helmet",
            11: "hands",
            14: "shoes",
            16: "safety-vest",
        }

    analyzer._model = _Model()
    assert analyzer._class_label(16) == "vest"
    assert analyzer._class_label(14) == "boots"
    assert analyzer._class_label(11) == "hand"
    assert analyzer._class_label(10) == "helmet"
