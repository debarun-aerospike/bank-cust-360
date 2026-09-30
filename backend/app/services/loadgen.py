"""Rate-limited read/write load workers for Admin load lab."""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field

from app.config import get_settings
from app.repositories import aerospike_repo as repo
from app.repositories.writes import overwrite_booking_bucket, touch_customer
from app.schemas.models import LoadState
from app.services import customer360
from app.services.metrics import metrics_hub


@dataclass
class LoadGenerator:
    state: LoadState = LoadState.stopped
    target_read_tps: int = 0
    target_write_tps: int = 0
    _stop: threading.Event = field(default_factory=threading.Event)
    _pause: threading.Event = field(default_factory=threading.Event)
    _threads: list[threading.Thread] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _rng: random.Random = field(default_factory=lambda: random.Random(42))

    def status(self) -> dict:
        snap = metrics_hub.snapshot()
        settings = get_settings()
        from app.services import ingest as ingest_mod

        seeded = ingest_mod.effective_customer_max or settings.seeded_customer_max
        return {
            "state": self.state,
            "targetReadTps": self.target_read_tps,
            "targetWriteTps": self.target_write_tps,
            "achievedReadTps": snap["readTps"],
            "achievedWriteTps": snap["writeTps"],
            "errorRate": snap["errorRate"],
            "latencyMs": snap["latencyMs"],
            "seededCustomerMax": seeded,
        }

    def configure(self, read_tps: int | None, write_tps: int | None) -> None:
        settings = get_settings()
        with self._lock:
            if read_tps is not None:
                self.target_read_tps = max(0, min(settings.max_read_tps, read_tps))
            if write_tps is not None:
                self.target_write_tps = max(0, min(settings.max_write_tps, write_tps))
            metrics_hub.set_targets(self.target_read_tps, self.target_write_tps)

    def start(self) -> None:
        with self._lock:
            if self.state == LoadState.running:
                return
            self._stop.clear()
            self._pause.clear()
            self.state = LoadState.running
            metrics_hub.set_targets(self.target_read_tps, self.target_write_tps)
            t_read = threading.Thread(target=self._read_loop, name="load-read", daemon=True)
            t_write = threading.Thread(target=self._write_loop, name="load-write", daemon=True)
            self._threads = [t_read, t_write]
            t_read.start()
            t_write.start()

    def pause(self) -> None:
        with self._lock:
            if self.state == LoadState.running:
                self._pause.set()
                self.state = LoadState.paused

    def resume(self) -> None:
        with self._lock:
            if self.state == LoadState.paused:
                self._pause.clear()
                self.state = LoadState.running

    def stop(self) -> None:
        with self._lock:
            self._stop.set()
            self._pause.clear()
            self.state = LoadState.stopped
            self.target_read_tps = 0
            self.target_write_tps = 0
            metrics_hub.set_targets(0, 0)
        for t in list(self._threads):
            t.join(timeout=2.0)
        self._threads = []
        # Clear rolling samples so latency/TPS charts idle immediately after Stop.
        metrics_hub.reset()

    def _wait_if_paused(self) -> None:
        while self._pause.is_set() and not self._stop.is_set():
            time.sleep(0.05)

    def _pick_customer(self) -> str:
        from app.services import ingest as ingest_mod

        n = ingest_mod.effective_customer_max or get_settings().seeded_customer_max
        n = max(1, int(n))
        return f"{self._rng.randint(1, n):07d}"

    def _read_loop(self) -> None:
        while not self._stop.is_set():
            self._wait_if_paused()
            tps = self.target_read_tps
            if tps <= 0 or self.state != LoadState.running:
                time.sleep(0.05)
                continue
            interval = 1.0 / tps
            start = time.perf_counter()
            cid = self._pick_customer()
            ok = True
            try:
                customer360.assemble_customer_360(cid)
            except Exception:  # noqa: BLE001
                ok = False
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            metrics_hub.record(kind="read", latency_ms=elapsed_ms, ok=ok)
            sleep_for = interval - (time.perf_counter() - start)
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _write_loop(self) -> None:
        while not self._stop.is_set():
            self._wait_if_paused()
            tps = self.target_write_tps
            if tps <= 0 or self.state != LoadState.running:
                time.sleep(0.05)
                continue
            interval = 1.0 / tps
            start = time.perf_counter()
            ok = True
            try:
                if self._rng.random() < 0.5:
                    cid = self._pick_customer()
                    touch_customer(cid, int(time.time() * 1000))
                else:
                    self._w2()
            except Exception:  # noqa: BLE001
                ok = False
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            metrics_hub.record(kind="write", latency_ms=elapsed_ms, ok=ok)
            sleep_for = interval - (time.perf_counter() - start)
            if sleep_for > 0:
                time.sleep(sleep_for)

    def _w2(self) -> None:
        cid = self._pick_customer()
        aids = repo.get_cust_accts(cid)
        if not aids:
            raise RuntimeError("no accounts")
        aid = self._rng.choice(aids)
        prefix = aid[0]
        if prefix in ("S", "F"):
            bin_name = self._rng.choice(["ledger", "hold", "float"])
            value = self._rng.randint(0, 1_000_000_00)
        else:
            bin_name = self._rng.choice(["principal", "interest"])
            value = self._rng.randint(0, 5_000_000_00)
        overwrite_booking_bucket(aid, bin_name, value)


load_generator = LoadGenerator()
