"""App-side latency / TPS aggregator for Admin WebSocket charts."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


@dataclass
class MetricsHub:
    window_seconds: int = 60
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _latencies_ms: Deque[tuple[float, float]] = field(default_factory=deque)  # (ts, ms)
    _read_ok: Deque[float] = field(default_factory=deque)
    _write_ok: Deque[float] = field(default_factory=deque)
    _errors: Deque[float] = field(default_factory=deque)
    target_read_tps: int = 0
    target_write_tps: int = 0

    def set_targets(self, read_tps: int, write_tps: int) -> None:
        with self._lock:
            self.target_read_tps = read_tps
            self.target_write_tps = write_tps

    def record(self, *, kind: str, latency_ms: float, ok: bool) -> None:
        now = time.time()
        with self._lock:
            self._trim(now)
            if ok:
                self._latencies_ms.append((now, latency_ms))
                if kind == "read":
                    self._read_ok.append(now)
                else:
                    self._write_ok.append(now)
            else:
                self._errors.append(now)

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._latencies_ms and self._latencies_ms[0][0] < cutoff:
            self._latencies_ms.popleft()
        while self._read_ok and self._read_ok[0] < cutoff:
            self._read_ok.popleft()
        while self._write_ok and self._write_ok[0] < cutoff:
            self._write_ok.popleft()
        while self._errors and self._errors[0] < cutoff:
            self._errors.popleft()

    def snapshot(self) -> dict:
        now = time.time()
        with self._lock:
            self._trim(now)
            # last 1s rates — live charts must not fall back to older samples
            # or latency stays non-zero after pause/stop.
            sec_cut = now - 1.0
            read_1s = sum(1 for t in self._read_ok if t >= sec_cut)
            write_1s = sum(1 for t in self._write_ok if t >= sec_cut)
            err_1s = sum(1 for t in self._errors if t >= sec_cut)
            total_1s = read_1s + write_1s + err_1s
            recent_sorted = sorted(ms for ts, ms in self._latencies_ms if ts >= sec_cut)
            if recent_sorted:
                latency = {
                    "p50": round(_percentile(recent_sorted, 0.50), 3),
                    "p99": round(_percentile(recent_sorted, 0.99), 3),
                    "p99_9": round(_percentile(recent_sorted, 0.999), 3),
                }
            else:
                latency = {"p50": 0.0, "p99": 0.0, "p99_9": 0.0}
            return {
                "ts": int(now * 1000),
                "readTps": float(read_1s),
                "writeTps": float(write_1s),
                "errorRate": (err_1s / total_1s) if total_1s else 0.0,
                "latencyMs": latency,
                "targetReadTps": self.target_read_tps,
                "targetWriteTps": self.target_write_tps,
            }

    def reset(self) -> None:
        """Drop rolling samples (e.g. after Stop) so charts go idle immediately."""
        with self._lock:
            self._latencies_ms.clear()
            self._read_ok.clear()
            self._write_ok.clear()
            self._errors.clear()
            self.target_read_tps = 0
            self.target_write_tps = 0



metrics_hub = MetricsHub()
