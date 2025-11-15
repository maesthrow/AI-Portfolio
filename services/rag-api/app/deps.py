from functools import lru_cache
from typing import Optional

import torch
from sentence_transformers import CrossEncoder

import chromadb
from chromadb.config import Settings as ChromaSettings

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma

from .settings import get_settings


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
def chat_llm() -> ChatOpenAI:
    s = settings()
    return ChatOpenAI(
        api_key=s.litellm_api_key or "EMPTY",
        base_url=str(s.litellm_base_url),
        model=s.chat_model,
        temperature=0.2,
        max_tokens=512,
        timeout=60,
    )
