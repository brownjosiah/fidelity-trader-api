"""Service configuration via environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8787
    encryption_key: str = ""
    db_path: str = "data/ftservice.db"
    api_key_required: bool = True
    auto_reauth: bool = True
    session_keepalive_interval: int = 300
    log_level: str = "INFO"
    live_trading: bool = False  # matches SDK dry-run default

    model_config = SettingsConfigDict(env_prefix="FTSERVICE_")
