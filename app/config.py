from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str
    app_version: str
    debug: bool
    host: str
    port: int
    api_prefix: str
    cors_origins: list[str]

    db_driver: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str

    redis_host: str
    redis_port: int
    redis_password: str
    redis_db: int
    redis_cache_ttl: int

    log_dir: str
    log_level: str
    log_file: str

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"{self.db_driver}://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            auth = f":{quote_plus(self.redis_password)}@"
        else:
            auth = ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
