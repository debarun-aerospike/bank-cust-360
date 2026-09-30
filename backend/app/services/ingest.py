"""Admin ingestion simulation — runs ops/seed/seed.py via uv."""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = ROOT / "ops" / "seed"

# Updated when ingest completes successfully; loadgen prefers this over settings default.
effective_customer_max: int | None = None


@dataclass
class IngestJob:
    state: str = "idle"
    target_customer_count: int | None = None
    country: str | None = None
    message: str | None = None
    last_exit_code: int | None = None
    _thread: threading.Thread | None = field(default=None, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def status(self) -> dict:
        return {
            "state": self.state,
            "targetCustomerCount": self.target_customer_count,
            "country": self.country,
            "message": self.message,
            "lastExitCode": self.last_exit_code,
        }

    def start(self, target: int, checkpoint_every: int, country: str = "India") -> None:
        with self._lock:
            if self.state == "running":
                raise RuntimeError("ingest already running")
            self.state = "running"
            self.target_customer_count = target
            self.country = (country or "India").strip() or "India"
            self.message = f"starting ({self.country})"
            self.last_exit_code = None
            self._thread = threading.Thread(
                target=self._run,
                args=(target, checkpoint_every, self.country),
                daemon=True,
                name="ingest",
            )
            self._thread.start()

    def _run(self, target: int, checkpoint_every: int, country: str) -> None:
        global effective_customer_max
        settings = get_settings()
        cmd = [
            "uv",
            "run",
            "python",
            "seed.py",
            "--customers",
            str(target),
            "--checkpoint-every",
            str(checkpoint_every),
            "--host",
            settings.aerospike_host,
            "--port",
            str(settings.aerospike_port),
            "--country",
            country,
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(SEED_DIR),
                capture_output=True,
                text=True,
                check=False,
            )
            self.last_exit_code = proc.returncode
            if proc.returncode == 0:
                self.state = "completed"
                lines = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
                self.message = lines[-1] if lines else "ok"
                effective_customer_max = target
            else:
                self.state = "failed"
                self.message = (proc.stderr or proc.stdout or "ingest failed")[-2000:]
        except Exception as exc:  # noqa: BLE001
            self.state = "failed"
            self.message = str(exc)
            self.last_exit_code = -1


ingest_job = IngestJob()
