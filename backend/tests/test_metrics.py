"""Metrics hub: live snapshot must idle when traffic stops."""

from __future__ import annotations

import time

from app.services.metrics import MetricsHub


def test_snapshot_latency_zeros_when_no_recent_samples() -> None:
    hub = MetricsHub(window_seconds=60)
    # Stale sample from 5s ago — must not keep latency non-zero.
    hub._latencies_ms.append((time.time() - 5.0, 12.5))
    hub._read_ok.append(time.time() - 5.0)
    snap = hub.snapshot()
    assert snap["readTps"] == 0.0
    assert snap["writeTps"] == 0.0
    assert snap["latencyMs"] == {"p50": 0.0, "p99": 0.0, "p99_9": 0.0}


def test_snapshot_latency_uses_last_second_only() -> None:
    hub = MetricsHub(window_seconds=60)
    now = time.time()
    hub._latencies_ms.append((now - 5.0, 100.0))
    hub._latencies_ms.append((now - 0.2, 4.0))
    hub._read_ok.append(now - 0.2)
    snap = hub.snapshot()
    assert snap["readTps"] == 1.0
    assert snap["latencyMs"]["p50"] == 4.0


def test_reset_clears_samples() -> None:
    hub = MetricsHub()
    hub.record(kind="read", latency_ms=3.0, ok=True)
    hub.set_targets(10, 2)
    hub.reset()
    snap = hub.snapshot()
    assert snap["readTps"] == 0.0
    assert snap["targetReadTps"] == 0
    assert snap["latencyMs"]["p50"] == 0.0
