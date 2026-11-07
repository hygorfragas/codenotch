import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_VISION_MOCK"] = "1"

import analyze_stream  # noqa: E402


def test_coreml_is_mac_only_and_yields_to_an_explicit_device(monkeypatch):
    monkeypatch.setattr(analyze_stream.sys, "platform", "darwin")
    monkeypatch.setenv("SNITCH_YOLO_DEVICE", "coreml")
    assert analyze_stream.coreml_requested()
    monkeypatch.setenv("SNITCH_YOLO_DEVICE", "mps")
    assert analyze_stream.coreml_requested() is False
    monkeypatch.setenv("SNITCH_YOLO_DEVICE", "cpu")
    assert analyze_stream.coreml_requested() is False
    monkeypatch.setattr(analyze_stream.sys, "platform", "linux")
    monkeypatch.setenv("SNITCH_YOLO_DEVICE", "coreml")
    assert analyze_stream.coreml_requested() is False


def test_coreml_env_does_not_become_the_pytorch_device(monkeypatch):
    monkeypatch.setenv("SNITCH_YOLO_DEVICE", "coreml")
    assert analyze_stream._resolve_device() in {"mps", "cpu"}


def test_an_explicit_pytorch_device_is_kept():
    os.environ["SNITCH_YOLO_DEVICE"] = "cpu"
    try:
        assert analyze_stream._resolve_device() == "cpu"
    finally:
        os.environ.pop("SNITCH_YOLO_DEVICE", None)
