"""Admin ingestion simulation — runs ops/seed/seed.py in a subprocess."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings

# Updated when ingest completes successfully; loadgen prefers this over settings default.
effective_customer_max: int | None = None


def resolve_seed_dir() -> Path:
    """Locate seed.py for monorepo (dev) or bundled Docker layout."""
    env = (os.environ.get("SEED_DIR") or "").strip()
    if env:
        return Path(env)

    here = Path(__file__).resolve()
    # .../customer360/backend/app/services/ingest.py → .../customer360/ops/seed
    mono = here.parents[3] / "ops" / "seed"
    if (mono / "seed.py").is_file():
        return mono
    # Container: /app/app/services/ingest.py → /app/ops/seed
    bundled = here.parents[2] / "ops" / "seed"
    if (bundled / "seed.py").is_file():
        return bundled
    return mono


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
        seed_dir = resolve_seed_dir()
        seed_py = seed_dir / "seed.py"
        if not seed_py.is_file():
            self.state = "failed"
            self.message = (
                f"seed script not found at {seed_py} "
                "(set SEED_DIR or bundle ops/seed into the backend image)"
            )
            self.last_exit_code = -1
            return

        cmd = [
            sys.executable,
            str(seed_py),
            "--customers",
            str(target),
            "--checkpoint-every",
            str(checkpoint_every),
            "--country",
            country,
        ]
        hosts = settings.aerospike_host_list()
        hosts_csv = ",".join(f"{h}:{p}" for h, p in hosts)
        cmd.extend(["--hosts", hosts_csv])
        if settings.aerospike_user:
            cmd.extend(["--user", settings.aerospike_user])
            cmd.extend(["--password", settings.aerospike_password or ""])
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(seed_dir),
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
