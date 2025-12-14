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
    chroma_collection: str = "portfolio_new"

    # CORS
    frontend_origin: str | AnyUrl = "http://localhost:3001"
    frontend_local_ip: str | AnyUrl = "http://localhost:3001"

    # logging
    log_level: str = "INFO"

    # === Feature flags (quality rollouts) ===
    rag_router_v2: bool = False  # Включить intent/entity-aware retrieval (план запроса, фильтры/буст по сущностям)
    rag_atomic_docs: bool = True  # Генерировать атомарные документы `type=item` для списков (achievements/tags/bullets/contacts/stats)
    rag_context_packer_v2: bool = False  # Упаковщик контекста v2: для списков сохранять пункты, для остальных — компактно
    agent_fact_tool: bool = False  # Агент использует инструмент факт-поиска (структурированные данные), а не готовый сгенерированный текст
    agent_memory_v2: bool = False  # Память диалога v2: follow-up детектор + summary (без “хвостов” из истории)

    # === Quality tuning ===
    rag_list_max_items: int = 16  # Максимум пунктов (items) для выдачи/контекста в списковых ответах
    rag_pack_budget_chars: int = 4200  # Бюджет символов на упакованный контекст, передаваемый в LLM
    agent_recent_turns: int = 3  # Сколько последних пар (вопрос/ответ) держать в “короткой” памяти
    agent_summary_trigger_turns: int = 6  # После скольких turns обновлять summary памяти
    agent_summary_max_chars: int = 1200  # Максимальная длина summary (символы)

    @property
    def chroma_client_kwargs(self) -> dict:
        return {"host": self.chroma_host, "port": self.chroma_port}


@lru_cache
def get_settings() -> Settings:
    # даём возможность принудительно указать путь к env
    _ = os.getenv("APP_ENV")  # не используем, но пусть остается для совместимости
    return Settings()
