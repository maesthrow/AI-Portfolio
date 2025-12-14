from __future__ import annotations

import logging
import math
from dataclasses import asdict
from typing import Any

from ..deps import reranker, settings, vectorstore, chat_llm
from .prompting import make_system_prompt, build_messages_for_answer, build_messages_when_empty
from .retrieval import HybridRetriever
from .rank import rerank
from .evidence import select_evidence, pack_context
from .context import pack_context_v2
from .types import ScoredDoc, SourceInfo

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


def _detect_intent(question: str) -> tuple[set[str] | None, str | None]:
    """
    Very lightweight intent routing to prefer правильные типы документов.
    """
    q = (question or "").lower()
    allowed = None
    style = None

    job_tokens = ("где работаешь", "где работает", "текущ", "сейчас работаешь", "current position")
    ach_tokens = ("достижен", "что сделал", "чем занимался", "результат")
    stack_tokens = ("стек", "технолог", "languages", "языки программирован", "какие бд", "какие базы")
    rag_tokens = ("rag", "агент", "agent", "retrieval", "langgraph")

    if any(t in q for t in job_tokens):
        allowed = {"profile", "experience", "experience_project"}
        style = "LIST"
    elif any(t in q for t in ach_tokens):
        allowed = {"experience", "experience_project", "project"}
        style = "LIST"
    elif any(t in q for t in stack_tokens):
        allowed = {"technology", "project", "tech_focus", "catalog"}
        style = "LIST"
    elif any(t in q for t in rag_tokens):
        allowed = {"project", "tech_focus", "technology", "experience_project"}
        style = "LIST"

    return allowed, style


def _compute_confidence(evidence: list[ScoredDoc], k: int) -> float:
    """
    Heuristic confidence score in [0..1] based on reranker scores of selected evidence.
    """
    if not evidence:
        return 0.0
    take = max(1, min(len(evidence), k))
    scores = [float(sd.score) for sd in evidence[:take]]
    avg = sum(scores) / len(scores)
    mx = max(scores)
    raw = 0.6 * avg + 0.4 * mx

    if 0.0 <= raw <= 1.0:
        base = raw
    else:
        try:
            base = 1.0 / (1.0 + math.exp(-raw))
        except OverflowError:
            base = 1.0 if raw > 0 else 0.0

    coverage = min(1.0, len(evidence) / max(1, k))
    conf = base * coverage
    return float(max(0.0, min(1.0, conf)))


def portfolio_rag_answer(
    question: str,
    k: int = 8,
    collection: str | None = None,
    extra_system: str | None = None,
) -> dict[str, Any]:
    cfg = settings()
    coll = collection or cfg.chroma_collection
    vs = vectorstore(coll)
    llm = chat_llm()
    rr = reranker()

    allowed_types, style_hint = _detect_intent(question)
    sys_prompt = make_system_prompt(extra_system)

    hybrid = HybridRetriever(vs, collection=coll)
    candidates_all = hybrid.retrieve(
        question,
        k_dense=max(k * 4, 40),
        k_bm=max(k * 4, 40),
        k_final=max(k * 3, k),
        allowed_types=allowed_types,
    )

    if not candidates_all:
        out = llm.invoke(build_messages_when_empty(sys_prompt, question, style_hint))
        return {
            "answer": out.content,
            "sources": [],
            "confidence": 0.0,
            "found": 0,
            "collection": coll,
            "model": cfg.chat_model,
        }

    scored: list[ScoredDoc] = rerank(rr, question, candidates_all)
    base = select_evidence(scored, question, k=k, min_k=max(k, 8))
    confidence = _compute_confidence(base, k=k)
    if cfg.rag_context_packer_v2:
        context = pack_context_v2(
            question,
            base,
            char_budget=cfg.rag_pack_budget_chars,
            max_items=cfg.rag_list_max_items,
        )
    else:
        context = pack_context(base, token_budget=900)

    out = llm.invoke(build_messages_for_answer(sys_prompt, question, context, style_hint, confidence=confidence))

    sources = _build_sources(base)
    sources_payload = [asdict(s) for s in sources]

    result = {
        "answer": out.content,
        "sources": sources_payload,
        "confidence": confidence,
        "found": len(candidates_all),
        "collection": coll,
        "model": cfg.chat_model,
    }

    logger.info(
        "portfolio_rag_answer: found=%s, allowed_types=%s, sources_count=%s",
        result["found"],
        allowed_types,
        len(sources_payload),
    )
    return result
