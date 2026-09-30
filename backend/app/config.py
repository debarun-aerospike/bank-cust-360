from __future__ import annotations

import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.aerospike_config import build_client_config, resolve_hosts


def _env_files() -> tuple[str, ...]:
    files = [".env"]
    extra = (os.environ.get("AEROSPIKE_CONFIG_FILE") or "").strip()
    if extra:
        files.append(extra)
    return tuple(files)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Prefer AEROSPIKE_HOSTS="ip1:3000,ip2:3000". Legacy single host still works.
    aerospike_hosts: str = ""
    aerospike_host: str = "127.0.0.1"
    aerospike_port: int = 13000
    aerospike_namespace: str = "bank"
    aerospike_user: str = ""
    aerospike_password: str = ""

    mock_auth_prefix: str = "mock:"
    admin_token: str = "admin:admin"

    max_read_tps: int = 5000
    max_write_tps: int = 5000

    # Loadgen picks customer IDs in [1, seeded_customer_max]
    seeded_customer_max: int = 100

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @field_validator("aerospike_user", "aerospike_password", "aerospike_hosts", mode="before")
    @classmethod
    def _none_to_empty(cls, v: object) -> object:
        return "" if v is None else v

    def aerospike_host_list(self) -> list[tuple[str, int]]:
        return resolve_hosts(
            hosts_csv=self.aerospike_hosts,
            single_host=self.aerospike_host,
            default_port=self.aerospike_port,
        )

    def aerospike_client_config(self) -> dict:
        return build_client_config(
            self.aerospike_host_list(),
            user=self.aerospike_user or None,
            password=self.aerospike_password or None,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
