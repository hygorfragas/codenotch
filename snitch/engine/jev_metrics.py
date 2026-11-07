"""Contadores leves das chamadas à Laya. Não guarda o corpo do pedido."""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((pct / 100) * (len(ordered) - 1)))))
    return ordered[index]


def _log_path() -> Path | None:
    chosen = os.environ.get("SNITCH_JEV_LOG", "").strip()
    if chosen == "0":
        return None
    if chosen:
        return Path(chosen)
    if Path("/weights").is_dir():
        return Path("/weights/jev-calls.jsonl")
    return Path("/tmp/snitch-jev-calls.jsonl")


class JevMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latencies: dict[str, deque[float]] = {}
        self._calls = 0
        self._errors = 0

    def record(
        self,
        *,
        endpoint: str,
        trigger: str,
        payload_bytes: int,
        latency_ms: float,
        status: str,
        decision: str | None,
    ) -> None:
        failed = status not in {"200", "ok"}
        with self._lock:
            self._calls += 1
            if failed:
                self._errors += 1
            bucket = self._latencies.setdefault(endpoint, deque(maxlen=400))
            bucket.append(float(latency_ms))
        row = {
            "ts": time.time(),
            "endpoint": endpoint,
            "trigger": trigger,
            "payload_bytes": int(payload_bytes),
            "latency_ms": round(float(latency_ms), 1),
            "status": status,
            "decision": decision,
        }
        path = _log_path()
        if path is None:
            return
        try:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            return

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            calls = self._calls
            errors = self._errors
            pooled = [value for bucket in self._latencies.values() for value in bucket]
            by_endpoint = {name: list(bucket) for name, bucket in self._latencies.items()}
        summary: dict[str, Any] = {
            "laya_calls": calls,
            "laya_errors": errors,
            "laya_error_rate": round(errors / calls, 3) if calls else 0.0,
            "laya_p50_ms": _round(_percentile(pooled, 50)),
            "laya_p95_ms": _round(_percentile(pooled, 95)),
        }
        for name, values in by_endpoint.items():
            key = name.strip("/").replace("/", "_") or "root"
            summary[f"laya_{key}_p50_ms"] = _round(_percentile(values, 50))
        return summary


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 1)


jev_metrics = JevMetrics()
