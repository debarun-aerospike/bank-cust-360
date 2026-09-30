"""Singleton Aerospike client for the process."""

from __future__ import annotations

import logging
from typing import Any

import aerospike

from app.config import get_settings

logger = logging.getLogger(__name__)

_client: Any | None = None


def get_client() -> Any:
    global _client
    if _client is None:
        raise RuntimeError("Aerospike client not initialized")
    return _client


def connect() -> Any:
    global _client
    if _client is not None:
        return _client
    settings = get_settings()
    hosts = [(settings.aerospike_host, settings.aerospike_port)]
    logger.info("Connecting Aerospike hosts=%s ns=%s", hosts, settings.aerospike_namespace)
    _client = aerospike.client({"hosts": hosts})
    return _client


def close() -> None:
    global _client
    if _client is not None:
        try:
            _client.close()
        finally:
            _client = None


def write_policy() -> dict:
    return {"key": aerospike.POLICY_KEY_SEND}


def ns() -> str:
    return get_settings().aerospike_namespace
