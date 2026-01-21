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

    # === TEI (embeddings) - direct access bypassing LiteLLM ===
    tei_base_url: str | AnyUrl = "http://tei:80/v1"

    # GigaChat
    giga_auth_data: str | None = None

    # Модели (алиасы, как в конфиге прокси)
    chat_model: str
    embedding_model: str = "text-embedding-3-large"
    embedding_batch_size: int = 4  # Small batch to avoid TEI 413 Payload Too Large

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-base"

    # Chroma
    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection: str = "portfolio_new"

    # CORS
    frontend_origin: str | AnyUrl = "http://localhost:3001"
    frontend_local_ip: str | AnyUrl = "http://localhost:3001"

    # logging
    log_level: str = "INFO"

     # === LLM temperatures ===
    planner_temperature: float = 0.0      # Planner LLM (детерминированный)
    answer_temperature: float = 0.2       # Answer LLM (баланс креативности)

    # === Critic settings ===
    critic_enabled: bool = True
    """Глобальное включение/выключение Critic LLM"""

    critic_confidence_threshold: float = 0.7
    """Порог confidence плана для пропуска Critic (>= threshold = skip)"""

    critic_min_facts_threshold: int = 2
    """Минимальное кол-во фактов для пропуска Critic (>= threshold = skip)"""

    critic_skip_intents: list[str] = ["contacts", "current_job"]
    """Список интентов где Critic всегда пропускается"""

    @property
    def chroma_client_kwargs(self) -> dict:
        return {"host": self.chroma_host, "port": self.chroma_port}


@lru_cache
def get_settings() -> Settings:
    # даём возможность принудительно указать путь к env
    _ = os.getenv("APP_ENV")  # не используем, но пусть остается для совместимости
    return Settings()
