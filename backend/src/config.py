from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_ignore_empty=True)

    app_env: str = "development"
    public_base_url: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg://wishlist:local-wishlist-password@db/wishlist"
    session_secret: str = ""
    dev_login_enabled: bool = False
    dev_user_id: str = "11111111-1111-4111-8111-111111111111"
    telegram_mode: str = "disabled"
    telegram_bot_token: str = ""
    telegram_chat_id: int | None = None
    telegram_bot_username: str = ""
    telegram_app_name: str = ""
    membership_ttl_seconds: int = 60
    session_ttl_seconds: int = 604800
    init_data_ttl_seconds: int = 300
    media_root: Path = Path("data/media")
    max_upload_bytes: int = 5 * 1024 * 1024
    max_image_pixels: int = 16_000_000
    metadata_max_bytes: int = 2 * 1024 * 1024
    metadata_timeout_seconds: float = 8
    unattached_media_ttl_hours: int = 24

    @model_validator(mode="after")
    def secure_configuration(self):
        base = urlsplit(self.public_base_url)
        if self.app_env not in {"development", "production", "test"}:
            raise ValueError("Unsupported APP_ENV")
        if base.scheme not in {"http", "https"} or not base.hostname or base.path not in {"", "/"}:
            raise ValueError("PUBLIC_BASE_URL must be an HTTP(S) origin")
        if base.username or base.password or base.query or base.fragment:
            raise ValueError("PUBLIC_BASE_URL must be an origin without credentials")
        if len(self.session_secret) < 32:
            raise ValueError("SESSION_SECRET must contain at least 32 characters")
        if self.dev_login_enabled and (
            self.app_env not in {"development", "test"}
            or base.hostname not in {"localhost", "127.0.0.1", "testserver"}
            or self.telegram_mode != "disabled"
        ):
            raise ValueError("Development login is only allowed locally with Telegram disabled")
        if self.app_env == "production" and base.scheme != "https":
            raise ValueError("Production requires HTTPS")
        if self.telegram_mode not in {"disabled", "polling"}:
            raise ValueError("Supported TELEGRAM_MODE values: disabled, polling")
        if self.telegram_mode != "disabled" and (not self.telegram_bot_token or not self.telegram_chat_id):
            raise ValueError("Telegram mode requires bot token and chat ID")
        if min(self.membership_ttl_seconds, self.session_ttl_seconds, self.init_data_ttl_seconds) <= 0:
            raise ValueError("TTL values must be positive")
        return self

    @property
    def origin(self) -> str:
        return self.public_base_url.rstrip("/")

    @property
    def secure_cookie(self) -> bool:
        return self.public_base_url.startswith("https://")


@lru_cache
def get_settings() -> Settings:
    return Settings()
