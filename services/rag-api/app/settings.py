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

    # === LiteLLM (единая точка для Chat/Embeddings) ===
    litellm_base_url: str | AnyUrl = "http://localhost:8005/v1"   # PROXY_URL/v1
    litellm_api_key: str = "sk-local-any"                         # любой токен (или реальный в проде)

    # Модели, зарегистрированные в LiteLLM (model_name из config.yaml)
    chat_model: str = "Qwen2.5"                 # алиас чата (локально идёт в vLLM)
    embedding_model: str = "embedding-default"  # алиас эмбеддингов (идёт в TEI/OpenAI — как настроишь)

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-base"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "portfolio"

    # CORS
    frontend_origin: str | AnyUrl = "http://localhost:3000"

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
