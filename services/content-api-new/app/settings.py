from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


def find_env_dev() -> Path | None:
    """
    Поднимаемся вверх от текущего файла и ищем infra/.env.dev.
    Как только нашли — возвращаем путь.
    """
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        candidate = p.parent.parent / "infra" / ".env.dev" if p.name == "app" else p / "infra" / ".env.dev"
        # пояснение:
        # если мы в .../services/content-api/app/settings.py, то p.name == "app"
        # и нам нужно подняться на два уровня к сервису и дальше к корню репо
        if candidate.exists():
            return candidate
    return None


ENV_DEV_PATH = find_env_dev()  # Path | None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # если нашли файл — читаем его, иначе просто читаем ОС окружение
        env_file=str(ENV_DEV_PATH) if ENV_DEV_PATH else None,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # CORS / логирование
    frontend_origin: str = "http://localhost:3000"
    log_level: str = "INFO"

    # Postgres (значения по умолчанию, если .env.dev не найден)
    postgres_user: str = "portfolio"
    postgres_password: str = "portfolio"
    postgres_db: str = "portfolio"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Если не задано — соберём ниже
    database_url: str | None = Field(default=None, description="SQLAlchemy DSN")

    def build_database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.database_url:
        s.database_url = s.build_database_url()
    return s


settings = get_settings()
