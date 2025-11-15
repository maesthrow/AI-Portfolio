import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # vLLM/OpenAI
    openai_base_url: str
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"

    # Chroma (наружный порт проброшен на 8001 в compose)
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "portfolio"

    # Postgres (локально: порт проброшен 5432)
    postgres_user: str = "portfolio"
    postgres_password: str = "portfolio"
    postgres_db: str = "portfolio"
    postgres_port: int = 5432
    postgres_host: str = "localhost"

    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache
def get_settings() -> Settings:
    env_file = os.getenv("APP_ENV", "./infra/.env.dev").lower()
    return Settings(_env_file=env_file, _env_file_encoding="utf-8")
