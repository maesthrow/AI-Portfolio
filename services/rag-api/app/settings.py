import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyUrl


def find_env_dev() -> Path | None:
    """
    Ищем ../infra/.env.dev, поднимаясь вверх от текущего файла.
    """
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        candidate = (p.parent.parent / "infra" / ".env.dev") if p.name == "app" else (p / "infra" / ".env.dev")
        if candidate.exists():
            return candidate
    return None


ENV_DEV_PATH = find_env_dev()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_DEV_PATH) if ENV_DEV_PATH else None,
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    # === LiteLLM (Qwen + embeddings) ===
    litellm_base_url: str | AnyUrl = "http://localhost:8005/v1"
    litellm_api_key: str = "sk-local-any"

    # GigaChat
    giga_auth_data: str | None = None

    # Модели (алиасы, как в конфиге прокси)
    chat_model: str
    embedding_model: str = "embedding-default"

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-base"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "portfolio"

    # CORS
    frontend_origin: str | AnyUrl = "http://localhost:3001"
    frontend_local_ip: str | AnyUrl = "http://localhost:3001"

    # logging
    log_level: str = "INFO"

    @property
    def chroma_client_kwargs(self) -> dict:
        return {"host": self.chroma_host, "port": self.chroma_port}


@lru_cache
def get_settings() -> Settings:
    # даём возможность принудительно указать путь к env
    _ = os.getenv("APP_ENV")  # не используем, но пусть остается для совместимости
    return Settings()
