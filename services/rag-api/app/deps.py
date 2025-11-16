from functools import lru_cache
from typing import Optional

import torch
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
    return OpenAIEmbeddings(
        api_key=s.litellm_api_key or "EMPTY",
        base_url=str(s.litellm_base_url),
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


@lru_cache()
def agent_app():
    """
    LangGraph-приложение (ReAct-агент) с памятью.
    """
    return build_agent_graph()
