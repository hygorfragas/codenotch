import os

import numpy as np

# Garante import do pacote engine
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ["SNITCH_VISION_MOCK"] = "1"

from analyze_stream import AnalyzeStreamConfig, StreamAnalyzer  # noqa: E402


def test_process_frame_mock_returns_state_and_image():
    config = AnalyzeStreamConfig(mock=True, camera_id=99)
    analyzer = StreamAnalyzer(config)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    annotated, state = analyzer.process_frame(frame)
    assert annotated.shape == frame.shape
    assert state["camera_id"] == 99
    assert "persons" in state
