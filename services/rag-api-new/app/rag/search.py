from __future__ import annotations

import logging
import math
from dataclasses import dataclass, replace
from typing import Any

from ..deps import reranker, settings, vectorstore
from .evidence import apply_entity_policy, select_evidence
from .query_plan import QueryPlan, build_query_plan
from .rank import rerank
from .retrieval import HybridRetriever
from .types import Doc, ScoredDoc, SourceInfo

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@dataclass(frozen=True)
class SearchResult:
    plan: QueryPlan
    candidates: list[Doc]
    scored: list[ScoredDoc]
    evidence: list[ScoredDoc]
    sources: list[SourceInfo]
    confidence: float
    found: int
    collection: str


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


def _compute_confidence(evidence: list[ScoredDoc], k: int) -> float:
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


def _merge_docs(*lists: list[Doc]) -> list[Doc]:
    seen = set()
    out: list[Doc] = []
    for docs in lists:
        for d in docs:
            did = (d.metadata or {}).get("doc_id") or (d.metadata or {}).get("ref_id")
            key = str(did) if did is not None else d.page_content[:64]
            if key in seen:
                continue
            seen.add(key)
            out.append(d)
    return out


def _retrieve_for_plan(hybrid: HybridRetriever, question: str, plan: QueryPlan) -> list[Doc]:
    """
    Retrieval с отдельным "item pass" (по item_kinds), чтобы не отсекать базовые документы фильтром `item_kind`.
    """
    base_types = set(plan.allowed_types) if plan.allowed_types else None
    item_kinds = set(plan.item_kinds or set())

    item_docs: list[Doc] = []
    if item_kinds and (base_types is None or "item" in base_types):
        where_item: dict[str, Any] = {"type": "item", "item_kind": {"$in": sorted(item_kinds)}}
        # Если есть явная сущность, можно попробовать фильтровать item-доки точнее.
        ent = plan.entities or []
        for e in ent:
            if e.kind == "project" and e.slug:
                where_item["project_slug"] = e.slug
                break
            if e.kind == "project" and e.key:
                where_item["project_name_key"] = e.key
                break
            if e.kind == "company" and e.slug:
                where_item["company_slug"] = e.slug
                break
            if e.kind == "company" and e.key:
                where_item["company_name_key"] = e.key
                break

        item_docs = hybrid.retrieve(
            question,
            k_dense=plan.k_dense,
            k_bm=plan.k_bm,
            k_final=plan.k_final,
            allowed_types={"item"},
            where=where_item,
            strict=True,
        )

    base_allowed = None if base_types is None else {t for t in base_types if t != "item"}
    base_docs: list[Doc] = []
    if base_allowed is None or base_allowed:
        base_docs = hybrid.retrieve(
            question,
            k_dense=plan.k_dense,
            k_bm=plan.k_bm,
            k_final=plan.k_final,
            allowed_types=base_allowed,
            where=plan.where,
            strict=True,
        )

    return _merge_docs(item_docs, base_docs)


def portfolio_search(
    question: str,
    *,
    k: int = 8,
    collection: str | None = None,
) -> SearchResult:
    cfg = settings()
    coll = collection or cfg.chroma_collection
    vs = vectorstore(coll)
    rr = reranker()

    plan = build_query_plan(question, collection=coll, list_max_items=cfg.rag_list_max_items)
    hybrid = HybridRetriever(vs, collection=coll)

    candidates_all = _retrieve_for_plan(hybrid, question, plan)
    if not candidates_all and plan.where is not None:
        # fallback: drop where-filter (например, если category='language' не совпала).
        plan = replace(plan, where=None)
        candidates_all = _retrieve_for_plan(hybrid, question, plan)

    scored: list[ScoredDoc] = rerank(rr, question, candidates_all)
    scored = apply_entity_policy(
        scored,
        entities=plan.entities,
        policy=plan.entity_policy.value,
        scope_types=plan.entity_scope_types,
    )

    evidence_k = max(int(k or 0), int(plan.evidence_k or 0))
    evidence = select_evidence(scored, question, k=evidence_k, min_k=evidence_k)
    confidence = _compute_confidence(evidence, k=evidence_k)

    # fallback: if strict is too narrow and confidence low — relax to boost.
    if plan.entity_policy.value == "strict" and confidence < plan.min_confidence_for_strict:
        relaxed = apply_entity_policy(
            scored,
            entities=plan.entities,
            policy="boost",
            scope_types=plan.entity_scope_types,
        )
        relaxed_evidence = select_evidence(relaxed, question, k=evidence_k, min_k=evidence_k)
        relaxed_conf = _compute_confidence(relaxed_evidence, k=evidence_k)
        if relaxed_conf >= confidence:
            evidence = relaxed_evidence
            confidence = relaxed_conf

    sources = _build_sources(evidence)

    logger.info(
        "portfolio_search: intent=%s, policy=%s, found=%s, evidence=%s",
        plan.intent.value,
        plan.entity_policy.value,
        len(candidates_all),
        len(evidence),
    )

    return SearchResult(
        plan=plan,
        candidates=candidates_all,
        scored=scored,
        evidence=evidence,
        sources=sources,
        confidence=confidence,
        found=len(candidates_all),
        collection=coll,
    )
