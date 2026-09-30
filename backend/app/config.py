from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    aerospike_host: str = "127.0.0.1"
    aerospike_port: int = 13000
    aerospike_namespace: str = "bank"

    mock_auth_prefix: str = "mock:"
    admin_token: str = "admin:admin"

    max_read_tps: int = 5000
    max_write_tps: int = 5000

    # Loadgen picks customer IDs in [1, seeded_customer_max]
    seeded_customer_max: int = 100

    api_host: str = "0.0.0.0"
    api_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
