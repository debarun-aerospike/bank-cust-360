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
    config = settings.aerospike_client_config()
    hosts = config["hosts"]
    auth = "on" if config.get("user") else "off"
    logger.info(
        "Connecting Aerospike hosts=%s ns=%s auth=%s",
        hosts,
        settings.aerospike_namespace,
        auth,
    )
    _client = aerospike.client(config)
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
