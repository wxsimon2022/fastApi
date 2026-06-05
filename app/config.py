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

    table_prefix: str
    table_users: str

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"{self.db_driver}://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
