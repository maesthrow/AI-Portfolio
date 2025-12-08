from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from ..deps import vectorstore, reranker, chat_llm, settings
from .prompting import (
    make_system_prompt,
    build_messages_for_answer,
    build_messages_when_empty,
)
from .retrieval import HybridRetriever
from .rank import rerank
from .evidence import select_evidence, pack_context
from .types import ScoredDoc, SourceInfo, Doc

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _build_sources(evidence: list[ScoredDoc]) -> list[SourceInfo]:
    srcs: list[SourceInfo] = []
    for sd in evidence:
        md = sd.doc.metadata or {}
        srcs.append(
            SourceInfo(
                id=md.get("ref_id") or md.get("id") or md.get("source"),
                type=md.get("type"),
                title=md.get("name") or md.get("title"),
                url=md.get("url") or md.get("repo_url") or md.get("demo_url"),
                kind=md.get("kind"),
                repo_url=md.get("repo_url"),
                demo_url=md.get("demo_url"),
                score=float(sd.score),
            )
        )
    return srcs


def portfolio_rag_answer(
    question: str,
    k: int = 8,
    collection: str | None = None,
    extra_system: str | None = None,
) -> dict[str, Any]:
    """
    Универсальный RAG-пайплайн портфолио:
    - hybrid retrieval (dense + BM25 через HybridRetriever)
    - rerank (CrossEncoder)
    - evidence filtering + упаковка контекста
    - LLM-ответ по системному промпту

    Возвращает dict, совместимый с текущим /ask.
    """
    cfg = settings()
    coll = collection or cfg.chroma_collection
    vs = vectorstore(coll)
    llm = chat_llm()
    rr = reranker()

    sys_prompt = make_system_prompt(extra_system)

    # 1) retrieval
    hybrid = HybridRetriever(vs, collection=coll)
    candidates_all = hybrid.retrieve(
        question,
        k_dense=max(k * 4, 40),
        k_bm=max(k * 4, 40),
        k_final=max(k * 3, k),
    )

    if not candidates_all:
        out = llm.invoke(
            build_messages_when_empty(sys_prompt, question)
        )
        return {
            "answer": out.content,
            "sources": [],
            "found": 0,
            "collection": coll,
            "model": cfg.chat_model,
        }

    # 2) rerank
    scored: list[ScoredDoc] = rerank(rr, question, candidates_all)

    # 3) evidence selection + упаковка контекста
    base = select_evidence(scored, question, k=k, min_k=max(k, 8))
    context = pack_context(base, token_budget=900)

    # 4) генерация ответа
    out = llm.invoke(
        build_messages_for_answer(sys_prompt, question, context)
    )

    sources = _build_sources(base)
    sources_payload = [asdict(s) for s in sources]

    result = {
        "answer": out.content,
        "sources": sources_payload,
        "found": len(candidates_all),
        "collection": coll,
        "model": cfg.chat_model,
    }

    logger.info(
        "portfolio_rag_answer:\n\nanswer=%s\n\nsources=%s\n\nfound=%s\n",
        result["answer"],
        result["sources"],
        result["found"],
    )

    return result
