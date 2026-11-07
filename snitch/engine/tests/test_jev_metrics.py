import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["SNITCH_JEV_LOG"] = "0"

from jev_metrics import JevMetrics, _percentile  # noqa: E402


def test_percentile_of_a_short_series():
    assert _percentile([10, 20, 30, 40, 50], 50) == 30
    assert _percentile([10, 20, 30, 40], 95) == 40
    assert _percentile([], 50) is None


def test_error_rate_counts_timeouts_and_not_the_body():
    metrics = JevMetrics()
    metrics.record(endpoint="/ask", trigger="any_missing_required_ppe", payload_bytes=80, latency_ms=100, status="200", decision="false")
    metrics.record(endpoint="/ask", trigger="any_person_in_restricted_zone", payload_bytes=90, latency_ms=900, status="timeout", decision=None)
    snapshot = metrics.snapshot()
    assert snapshot["laya_calls"] == 2
    assert snapshot["laya_errors"] == 1
    assert snapshot["laya_error_rate"] == 0.5
    assert snapshot["laya_p50_ms"] == 100
