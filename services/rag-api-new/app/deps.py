from functools import lru_cache
from typing import Optional
import logging

import threading

import torch
from sentence_transformers import CrossEncoder

from sqlalchemy import text as sa_text

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGEngine, PGVectorStore, Column

from .agent.graph import build_agent_graph
from .llm.factory import get_llm_factory
from .settings import get_settings


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@lru_cache()
def settings():
    return get_settings()


@lru_cache()
def embeddings() -> Embeddings:
    s = settings()
    if s.embedding_provider == "gigachat":
        if not s.giga_auth_data:
            raise RuntimeError(
                "EMBEDDING_PROVIDER=gigachat requires GIGA_AUTH_DATA to be set"
            )
        from langchain_gigachat import GigaChatEmbeddings
        logger.info("Embedding provider: gigachat (model=%s)", s.embedding_model)
        return GigaChatEmbeddings(
            credentials=s.giga_auth_data,
            model=s.embedding_model,
            verify_ssl_certs=False,
            timeout=60,
        )
    # Default: TEI (bypassing LiteLLM which adds unsupported encoding_format)
    logger.info("Embedding provider: tei (url=%s)", s.tei_base_url)
    return OpenAIEmbeddings(
        api_key="dummy",
        base_url=str(s.tei_base_url),
        model=s.embedding_model,
    )


_METADATA_COLUMNS = [
    Column("type", "TEXT"),
    Column("project_id", "TEXT"),
    Column("ref_id", "TEXT"),
    Column("doc_id", "TEXT"),
]

_METADATA_COLUMN_NAMES = ["type", "project_id", "ref_id", "doc_id"]


_pg_engine_instance: PGEngine | None = None
_pg_engine_lock = threading.Lock()
_embedding_dim: int | None = None


def _detect_embedding_dim() -> int:
    """Determine vector dimension by running a test embedding."""
    global _embedding_dim
    if _embedding_dim is not None:
        return _embedding_dim
    vec = embeddings().embed_query("test")
    _embedding_dim = len(vec)
    logger.info("Detected embedding dimension: %d", _embedding_dim)
    return _embedding_dim


def get_embedding_dim() -> int | None:
    """Return cached embedding dimension (None if not yet detected)."""
    return _embedding_dim


def _get_table_vector_dim(engine: PGEngine, table_name: str) -> int | None:
    """Query existing pgvector column dimension from pg_attribute catalog."""
    async def _query():
        async with engine._pool.connect() as conn:
            result = await conn.execute(
                sa_text(
                    "SELECT atttypmod - 4 FROM pg_attribute "
                    "WHERE attrelid = CAST(:tbl AS regclass) AND attname = 'embedding' "
                    "AND atttypmod > 0"
                ),
                {"tbl": table_name},
            )
            row = result.fetchone()
            return row[0] if row else None

    try:
        return engine._run_as_sync(_query())
    except Exception as exc:
        logger.debug("_get_table_vector_dim failed: %s", exc)
        return None  # Table doesn't exist yet


def pg_engine() -> PGEngine:
    global _pg_engine_instance
    if _pg_engine_instance is not None:
        return _pg_engine_instance
    with _pg_engine_lock:
        if _pg_engine_instance is not None:
            return _pg_engine_instance
        s = settings()
        engine = PGEngine.from_connection_string(url=s.database_url)

        detected_dim = _detect_embedding_dim()
        existing_dim = _get_table_vector_dim(engine, s.collection_name)

        if existing_dim is not None and existing_dim != detected_dim:
            logger.warning(
                "Dimension mismatch: table '%s' has %d-dim vectors, "
                "but current embedding provider produces %d-dim. "
                "Recreating table...",
                s.collection_name, existing_dim, detected_dim,
            )
            engine.init_vectorstore_table(
                table_name=s.collection_name,
                vector_size=detected_dim,
                metadata_columns=_METADATA_COLUMNS,
                overwrite_existing=True,
                store_metadata=True,
            )
            try:
                from .cache import invalidate_embedding_cache
                deleted = invalidate_embedding_cache()
                logger.info("Cleared %d embedding cache entries", deleted)
            except Exception as exc:
                logger.warning("Failed to clear embedding cache: %s", exc)
            logger.info(
                "Table '%s' recreated with vector_size=%d, reingest required",
                s.collection_name, detected_dim,
            )
        else:
            try:
                engine.init_vectorstore_table(
                    table_name=s.collection_name,
                    vector_size=detected_dim,
                    metadata_columns=_METADATA_COLUMNS,
                    overwrite_existing=False,
                    store_metadata=True,
                )
                logger.info(
                    "pgvector table '%s' created (vector_size=%d)",
                    s.collection_name, detected_dim,
                )
            except Exception as exc:
                if "DuplicateTable" in type(exc).__name__ or "already exists" in str(exc):
                    logger.info(
                        "pgvector table '%s' already exists (vector_size=%s), skipping init",
                        s.collection_name, existing_dim or "unknown",
                    )
                else:
                    raise

        _pg_engine_instance = engine
        return engine


def vectorstore(collection: Optional[str] = None) -> PGVectorStore:
    s = settings()
    return PGVectorStore.create_sync(
        engine=pg_engine(),
        table_name=collection or s.collection_name,
        embedding_service=embeddings(),
        metadata_columns=_METADATA_COLUMN_NAMES,
    )


@lru_cache()
def reranker() -> CrossEncoder:
    s = settings()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    return CrossEncoder(
        s.reranker_model,
        device=device,
        trust_remote_code=True
    )


# =============================================================================
# LLM Functions (via LLMFactory)
# =============================================================================


@lru_cache()
def identity_llm() -> BaseChatModel:
    """
    LLM для Identity (ответы на 'кто ты?', 'что умеешь?').

    Использует настройки из settings.identity_llm и settings.identity_temperature.
    """
    s = settings()
    factory = get_llm_factory()
    logger.info("Creating identity LLM: %s (temp=%.2f)", s.identity_llm, s.identity_temperature)
    return factory.create(
        llm_id=s.identity_llm,
        temperature=s.identity_temperature,
        max_tokens=512,
    )


@lru_cache()
def planner_llm() -> BaseChatModel:
    """
    LLM для Planner (планирование запросов).

    Использует temperature=0.0 для детерминированного вывода.
    """
    s = settings()
    factory = get_llm_factory()
    logger.info("Creating planner LLM: %s (temp=%.2f)", s.planner_llm, s.planner_temperature)
    return factory.create(
        llm_id=s.planner_llm,
        temperature=s.planner_temperature,
        max_tokens=1024,
    )


@lru_cache()
def answer_llm() -> BaseChatModel:
    """
    LLM для Answer (генерация ответов).

    Использует настройки из settings.answer_llm и settings.answer_temperature.
    """
    s = settings()
    factory = get_llm_factory()
    logger.info("Creating answer LLM: %s (temp=%.2f)", s.answer_llm, s.answer_temperature)
    return factory.create(
        llm_id=s.answer_llm,
        temperature=s.answer_temperature,
        max_tokens=1024,
    )


@lru_cache()
def critic_llm() -> BaseChatModel:
    """
    LLM для Critic (оценка достаточности фактов).

    Использует настройки из settings.critic_llm и settings.critic_temperature.
    """
    s = settings()
    factory = get_llm_factory()
    logger.info("Creating critic LLM: %s (temp=%.2f)", s.critic_llm, s.critic_temperature)
    return factory.create(
        llm_id=s.critic_llm,
        temperature=s.critic_temperature,
        max_tokens=512,
    )


@lru_cache()
def agent_llm() -> BaseChatModel:
    """
    LLM для Agent (ReAct orchestration).

    Использует настройки из settings.agent_llm и settings.agent_temperature.
    """
    s = settings()
    factory = get_llm_factory()
    logger.info("Creating agent LLM: %s (temp=%.2f)", s.agent_llm, s.agent_temperature)
    return factory.create(
        llm_id=s.agent_llm,
        temperature=s.agent_temperature,
        max_tokens=512,
    )


@lru_cache()
def router_llm() -> BaseChatModel:
    """LLM для Router (intent classification fallback).

    Дешёвая модель (DeepSeek-chat) с temperature=0 для
    детерминированной классификации. Вызывается только когда
    regex fast-path не сработал (~30% сообщений).
    """
    s = settings()
    factory = get_llm_factory()
    logger.info("Creating router LLM: %s (temp=%.2f)", s.router_llm, s.router_temperature)
    return factory.create(
        llm_id=s.router_llm,
        temperature=s.router_temperature,
        max_tokens=32,
    )


# =============================================================================
# Application Components
# =============================================================================


@lru_cache()
def agent_app():
    """
    LangGraph-приложение (ReAct-агент) с памятью.
    """
    return build_agent_graph()


def graph_store():
    """
    Получить хранилище графа знаний.

    Не кэшируется через lru_cache, т.к. граф может перестраиваться при инжесте.
    """
    from .graph.store import get_graph_store
    return get_graph_store()


@lru_cache()
def email_service():
    """Email service singleton for CV sending."""
    from .email import EmailService
    svc = EmailService(settings())
    if not svc.available:
        logger.warning("EmailService: SMTP not configured, CV sending will be unavailable")
    return svc


@lru_cache()
def rate_limiter():
    """
    Rate limiter singleton.

    Ограничивает использование LLM токенов по сессии и IP.
    """
    from .rate_limit import RateLimiter
    return RateLimiter(settings())
