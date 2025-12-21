"""
Portfolio Search - оркестратор поиска.

Объединяет Graph-RAG и гибридный поиск в единый интерфейс.
Использует QueryPlan для выбора оптимальной стратегии.
"""
from __future__ import annotations

import re
import logging
from dataclasses import asdict
from typing import Any, List

from ..deps import settings, vectorstore, reranker
from ..graph.query import graph_query
from .query_plan import plan_query
from .search_types import SearchResult, Intent, EntityPolicy, Entity, EntityType
from .retrieval import HybridRetriever
from .rank import rerank
from .evidence import select_evidence, pack_context
from .types import ScoredDoc, SourceInfo, Doc

logger = logging.getLogger(__name__)


def _build_sources(evidence: List[ScoredDoc]) -> List[dict[str, Any]]:
    """Построить список источников из evidence."""
    srcs: List[dict[str, Any]] = []
    for sd in evidence:
        md = sd.doc.metadata or {}
        src = SourceInfo(
            id=md.get("ref_id") or md.get("id") or md.get("source"),
            type=md.get("type"),
            title=md.get("name") or md.get("title"),
            url=md.get("url") or md.get("repo_url") or md.get("demo_url"),
            kind=md.get("kind"),
            repo_url=md.get("repo_url"),
            demo_url=md.get("demo_url"),
            score=float(sd.score),
        )
        srcs.append(asdict(src))
    return srcs


def _apply_entity_filter(docs: List[Doc], entities: List[Entity], policy: EntityPolicy) -> List[Doc]:
    """
    Применить фильтрацию по сущностям.

    - STRICT: оставить только документы с указанными сущностями
    - BOOST: переместить документы с сущностями в начало
    - NONE: без изменений
    """
    if policy == EntityPolicy.NONE or not entities:
        return docs

    entity_slugs = {e.slug.lower() for e in entities}
    entity_names = {e.name.lower() for e in entities}

    def _token_match(text: str, token: str) -> bool:
        token = (token or "").strip().lower()
        if not token:
            return False
        tl = (text or "").lower()
        if not tl:
            return False
        if len(token) <= 3 and token.isalnum():
            return re.search(rf"(?<![\\w-]){re.escape(token)}(?![\\w-])", tl) is not None
        return token in tl

    def _value_matches(val: Any) -> bool:
        if val is None:
            return False
        if isinstance(val, (list, tuple, set)):
            return any(_value_matches(v) for v in val)
        if not isinstance(val, str):
            val = str(val)
        val_lower = val.lower()
        if val_lower in entity_slugs or val_lower in entity_names:
            return True
        for tok in entity_slugs:
            if _token_match(val_lower, tok):
                return True
        for tok in entity_names:
            if _token_match(val_lower, tok):
                return True
        return False

    def matches_entity(doc: Doc) -> bool:
        md = doc.metadata or {}
        for key in ["slug", "project_slug", "company_slug", "name", "title", "ref_id"]:
            val = md.get(key)
            if isinstance(val, str):
                val_lower = val.lower()
                if val_lower in entity_slugs or val_lower in entity_names:
                    return True
                # Частичное совпадение
                for slug in entity_slugs:
                    if slug in val_lower or val_lower in slug:
                        return True
        return False

    def matches_entity_ext(doc: Doc) -> bool:
        md = doc.metadata or {}
        for key in [
            "slug",
            "project_slug",
            "company_slug",
            "name",
            "title",
            "ref_id",
            "technologies",
            "technologies_csv",
            "tags",
            "tags_csv",
            "project_names",
            "project_names_csv",
        ]:
            if _value_matches(md.get(key)):
                return True
        return _value_matches(doc.page_content or "")

    if policy == EntityPolicy.STRICT:
        filtered = [d for d in docs if matches_entity_ext(d)]
        # Если STRICT вернул пусто, возвращаем исходные (fallback)
        if filtered:
            return filtered
        # Если вопрос только про технологию и нет матчей — лучше вернуть пусто,
        # чтобы агент детерминированно ответил "не найдено". При смешанных
        # сущностях (технология + человек/компания) не режем выдачу полностью,
        # иначе получаем ложные "NO_RESULTS" из-за несовпадения slug/alias.
        if entities and all(e.type == EntityType.TECHNOLOGY for e in entities):
            return []
        return docs

    # BOOST: matching первыми
    matching = [d for d in docs if matches_entity_ext(d)]
    non_matching = [d for d in docs if not matches_entity_ext(d)]
    return matching + non_matching


def portfolio_search(
    question: str,
    k: int = 8,
    collection: str | None = None,
    allowed_types: set[str] | list[str] | None = None,
) -> SearchResult:
    """
    Унифицированный поиск по портфолио.

    1. Проверяет feature flag rag_router_v2
    2. Генерирует QueryPlan
    3. Если use_graph: пробует graph_query
    4. Иначе/fallback: гибридный поиск
    5. Возвращает SearchResult

    Args:
        question: Вопрос пользователя
        k: Количество результатов
        collection: Название коллекции (опционально)

    Returns:
        SearchResult с найденными фактами или evidence
    """
    cfg = settings()
    coll = collection or cfg.chroma_collection

    # === Feature flag check ===
    # v3 (planner_llm_v3=true) uses this module as a retrieval tool, so avoid the
    # legacy portfolio_rag_answer() path (it already generates an answer).
    if not cfg.rag_router_v2 and not cfg.planner_llm_v3:
        # Fallback на старый portfolio_rag_answer
        from .core import portfolio_rag_answer
        result = portfolio_rag_answer(question, k=k, collection=coll)
        return SearchResult(
            query=question,
            intent=Intent.GENERAL,
            entities=[],
            items=[],
            evidence=result.get("answer", ""),
            sources=result.get("sources", []),
            confidence=result.get("confidence", 0.0),
            found=result.get("found", 0) > 0,
            used_graph=False,
        )

    # === Generate QueryPlan ===
    plan = plan_query(question, use_graph_feature=cfg.graph_rag_enabled)
    if allowed_types:
        plan.allowed_types = set(allowed_types)

    logger.info(
        "QueryPlan: intent=%s, entities=%s, use_graph=%s, entity_policy=%s",
        plan.intent.value,
        [e.slug for e in plan.entities],
        plan.use_graph,
        plan.entity_policy.value,
    )

    # === Try Graph Query ===
    if plan.use_graph and cfg.graph_rag_enabled:
        entity_key = plan.entities[0].slug if plan.entities else None
        graph_result = graph_query(plan.intent, entity_key)

        logger.info(
            "Graph query: found=%s, items=%d, confidence=%.2f",
            graph_result.found,
            len(graph_result.items),
            graph_result.confidence,
        )

        # Если граф дал хорошие результаты
        if graph_result.found and graph_result.confidence >= 0.7:
            return SearchResult(
                query=question,
                intent=plan.intent,
                entities=plan.entities,
                items=graph_result.items,
                evidence="",  # Форматирование на стороне вызывающего кода
                sources=graph_result.sources,
                confidence=graph_result.confidence,
                found=True,
                used_graph=True,
            )

    # === Fallback to Hybrid Retrieval ===
    vs = vectorstore(coll)
    rr = reranker()

    hybrid = HybridRetriever(vs, collection=coll)
    candidates = hybrid.retrieve(
        question,
        k_dense=plan.k_dense,
        k_bm=plan.k_bm,
        k_final=plan.k_final,
        allowed_types=plan.allowed_types,
    )

    if not candidates:
        return SearchResult(
            query=question,
            intent=plan.intent,
            entities=plan.entities,
            items=[],
            evidence="",
            sources=[],
            confidence=0.0,
            found=False,
            used_graph=False,
        )

    # === Apply Entity Filter ===
    candidates = _apply_entity_filter(candidates, plan.entities, plan.entity_policy)

    # === Rerank ===
    scored: List[ScoredDoc] = rerank(rr, question, candidates)
    evidence_docs = select_evidence(scored, question, k=k, min_k=max(k, 8))

    # === Compute Confidence ===
    if evidence_docs:
        scores = [float(sd.score) for sd in evidence_docs[:k]]
        avg = sum(scores) / len(scores)
        confidence = min(1.0, max(0.0, avg))
    else:
        confidence = 0.0

    logger.info(
        "evidence_docs: %s",
        [f'{e}\n' for e in evidence_docs],
    )

    # === Pack Context ===
    context = pack_context(evidence_docs, token_budget=900)
    sources = _build_sources(evidence_docs)

    return SearchResult(
        query=question,
        intent=plan.intent,
        entities=plan.entities,
        items=[],  # При гибридном поиске items пустой
        evidence=context,
        sources=sources,
        confidence=confidence,
        found=len(evidence_docs) > 0,
        used_graph=False,
    )
