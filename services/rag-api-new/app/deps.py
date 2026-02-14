from functools import lru_cache
from typing import Optional
import logging

import torch
from sentence_transformers import CrossEncoder

import chromadb
from chromadb.config import Settings as ChromaSettings

from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

from .agent.graph import build_agent_graph
from .llm.factory import get_llm_factory
from .settings import get_settings


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@lru_cache()
def settings():
    return get_settings()


@lru_cache()
def embeddings() -> OpenAIEmbeddings:
    s = settings()
    # Use TEI directly (bypassing LiteLLM which adds unsupported encoding_format)
    return OpenAIEmbeddings(
        api_key="dummy",
        base_url=str(s.tei_base_url),
        model=s.embedding_model,
    )


@lru_cache()
def chroma_client() -> chromadb.HttpClient:
    s = settings()
    return chromadb.HttpClient(
        host=s.chroma_host,
        port=s.chroma_port,
        settings=ChromaSettings(allow_reset=False),
    )


def vectorstore(collection: Optional[str] = None) -> Chroma:
    s = settings()
    return Chroma(
        client=chroma_client(),
        collection_name=collection or s.chroma_collection,
        embedding_function=embeddings(),
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
