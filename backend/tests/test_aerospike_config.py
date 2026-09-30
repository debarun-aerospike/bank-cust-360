"""Unit tests for Aerospike host parsing (no cluster required)."""

from __future__ import annotations

from app.aerospike_config import build_client_config, parse_hosts, resolve_hosts


def test_parse_hosts_mixed() -> None:
    assert parse_hosts("10.0.0.1:3000, 10.0.0.2", 3000) == [
        ("10.0.0.1", 3000),
        ("10.0.0.2", 3000),
    ]


def test_resolve_hosts_prefers_csv() -> None:
    assert resolve_hosts(
        hosts_csv="a:3000,b:3001",
        single_host="127.0.0.1",
        default_port=13000,
    ) == [("a", 3000), ("b", 3001)]


def test_resolve_hosts_legacy_single() -> None:
    assert resolve_hosts(hosts_csv="", single_host="db.example", default_port=3000) == [
        ("db.example", 3000)
    ]


def test_build_client_config_auth_optional() -> None:
    bare = build_client_config([("h", 3000)])
    assert "user" not in bare
    auth = build_client_config([("h", 3000)], user="admin", password="secret")
    assert auth["user"] == "admin"
    assert auth["password"] == "secret"
