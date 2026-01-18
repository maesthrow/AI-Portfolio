from functools import lru_cache
from typing import Optional, TYPE_CHECKING

import torch

if TYPE_CHECKING:
    from .cache import ResponseCache
from sentence_transformers import CrossEncoder

import chromadb
from chromadb.config import Settings as ChromaSettings

from langchain_core.language_models import BaseChatModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma

from langchain_gigachat.chat_models import GigaChat
from .agent.graph import build_agent_graph

from .settings import get_settings
import logging


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


@lru_cache()
def chat_llm() -> BaseChatModel:
    s = settings()

    logger.info(f"chat_model={s.chat_model}")

    # если GigaChat
    if s.chat_model.lower().startswith("gigachat"):
        logger.info(f"LLM is gigachat")
        return GigaChat(
            credentials=s.giga_auth_data,
            model=s.chat_model,            # "gigachat" / "gigachat-2" / "gigachat-pro" и т.п.
            verify_ssl_certs=False,
        )

    # иначе – идём через LiteLLM / Qwen
    return ChatOpenAI(
        api_key=s.litellm_api_key or "EMPTY",
        base_url=str(s.litellm_base_url),
        model=s.chat_model,              # "Qwen2.5"
        temperature=0.2,
        max_tokens=512,
        timeout=60,
    )


def _create_llm_with_temperature(temperature: float) -> BaseChatModel:
    """Create LLM with specific temperature."""
    s = settings()

    if s.chat_model.lower().startswith("gigachat"):
        return GigaChat(
            credentials=s.giga_auth_data,
            model=s.chat_model,
            verify_ssl_certs=False,
            temperature=temperature,
        )

    return ChatOpenAI(
        api_key=s.litellm_api_key or "EMPTY",
        base_url=str(s.litellm_base_url),
        model=s.chat_model,
        temperature=temperature,
        max_tokens=1024,
        timeout=60,
    )


@lru_cache()
def planner_llm() -> BaseChatModel:
    """
    LLM для Planner (планирование запросов).

    Использует temperature=0.0 для детерминированного вывода.
    """
    s = settings()
    logger.info("Creating planner LLM with temperature=%.2f", s.planner_temperature)
    return _create_llm_with_temperature(s.planner_temperature)


@lru_cache()
def answer_llm() -> BaseChatModel:
    """
    LLM для Answer (генерация ответов).

    Использует temperature=0.3 для баланса креативности и точности.
    """
    s = settings()
    logger.info("Creating answer LLM with temperature=%.2f", s.answer_temperature)
    return _create_llm_with_temperature(s.answer_temperature)


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


# === Response Cache ===

_response_cache_instance: Optional["ResponseCache"] = None


def response_cache() -> Optional["ResponseCache"]:
    """
    Получить экземпляр кэша ответов.

    Возвращает None если кэширование отключено.
    Использует lazy initialization для избежания circular imports.
    """
    global _response_cache_instance

    s = settings()

    if not s.cache_enabled:
        return None

    if _response_cache_instance is not None:
        return _response_cache_instance

    # Lazy import to avoid circular dependencies
    from .cache import ResponseCache

    _response_cache_instance = ResponseCache(
        chroma_client=chroma_client(),
        collection_name=s.cache_collection,
        embeddings=embeddings(),
        similarity_threshold=s.cache_similarity_threshold,
    )

    logger.info(
        "Response cache initialized: collection=%s, threshold=%.2f",
        s.cache_collection,
        s.cache_similarity_threshold,
    )

    return _response_cache_instance


def reset_response_cache() -> None:
    """
    Сбросить экземпляр кэша (для тестов и ре-инициализации).
    """
    global _response_cache_instance
    _response_cache_instance = None
