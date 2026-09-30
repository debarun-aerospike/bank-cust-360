"""Parse Aerospike seed hosts and build client config from settings / env."""

from __future__ import annotations

from typing import Any


def parse_hosts(hosts_csv: str, default_port: int) -> list[tuple[str, int]]:
    """
    Parse a comma-separated seed list.

    Accepted forms per entry:
      - host
      - host:port
    Empty / whitespace entries are skipped.
    """
    out: list[tuple[str, int]] = []
    for part in (hosts_csv or "").split(","):
        item = part.strip()
        if not item:
            continue
        if ":" in item:
            host, _, port_s = item.rpartition(":")
            host = host.strip()
            if not host:
                continue
            try:
                port = int(port_s.strip())
            except ValueError as exc:
                raise ValueError(f"Invalid Aerospike host entry {item!r}") from exc
            out.append((host, port))
        else:
            out.append((item, default_port))
    return out


def resolve_hosts(
    *,
    hosts_csv: str | None,
    single_host: str | None,
    default_port: int,
) -> list[tuple[str, int]]:
    """Prefer AEROSPIKE_HOSTS; fall back to AEROSPIKE_HOST + AEROSPIKE_PORT."""
    if hosts_csv and hosts_csv.strip():
        hosts = parse_hosts(hosts_csv, default_port)
        if hosts:
            return hosts
    host = (single_host or "127.0.0.1").strip() or "127.0.0.1"
    return [(host, default_port)]


def build_client_config(
    hosts: list[tuple[str, int]],
    *,
    user: str | None = None,
    password: str | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {"hosts": hosts}
    u = (user or "").strip()
    if u:
        config["user"] = u
        config["password"] = password or ""
    return config
