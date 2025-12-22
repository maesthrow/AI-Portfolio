"""
Portfolio Search Tool - wrapper for hybrid retrieval.

Executes full-text search with semantic and BM25 ranking.
Supports V3 filters: types, tech_category, company_id, min_score.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..planner.schemas import FactItem

logger = logging.getLogger(__name__)


def execute_portfolio_search(
    query: str,
    k: int = 8,
    allowed_types: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    min_score: float | None = None,
    tech_category: str | None = None,
) -> tuple[list[FactItem], list[dict[str, Any]], bool, float, str]:
    """
    Execute a portfolio search and return facts.

    Args:
        query: Search query
        k: Number of results to return
        allowed_types: Optional list of document types to filter
        filters: Additional filters (company_id, project_id, tech_category, tags_any)
        min_score: Minimum relevance score threshold (0.0-1.0)
        tech_category: Filter technologies by category

    Returns:
        Tuple of (facts, sources, found, confidence, evidence_text)
    """
    from ...rag.search import portfolio_search

    # Merge tech_category into filters
    effective_filters = dict(filters) if filters else {}
    if tech_category:
        effective_filters["tech_category"] = tech_category

    logger.info(
        "portfolio_search: query=%r, k=%d, types=%s, filters=%s, min_score=%s",
        query[:50],
        k,
        allowed_types,
        effective_filters,
        min_score,
    )

    # Execute search
    result = portfolio_search(
        question=query,
        k=k,
        allowed_types=allowed_types,
        filters=effective_filters if effective_filters else None,
        min_score=min_score,
    )

    # Convert items to FactItem
    facts = []
    for item in result.items:
        fact = _item_to_fact(item, result.intent)
        if fact:
            facts.append(fact)

    # Hybrid search returns only evidence; convert it to facts so the answer stage
    # can be deterministic (and UI can display rendered_facts/items).
    if not facts and result.evidence:
        facts = _evidence_to_facts(result.evidence)

    return (
        facts,
        result.sources,
        result.found,
        result.confidence,
        result.evidence,
    )


def _item_to_fact(item: Any, intent: Any) -> FactItem | None:
    """Convert a search result item to FactItem."""
    # Handle ScoredDoc objects
    if hasattr(item, "doc"):
        doc = item.doc
        text = doc.page_content if hasattr(doc, "page_content") else str(doc)
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        return FactItem(
            type=metadata.get("type", "document"),
            text=text,
            metadata=metadata,
            source_id=metadata.get("id"),
        )

    # Handle dict items
    if isinstance(item, dict):
        text = (
            item.get("text")
            or item.get("page_content")
            or item.get("content")
            or str(item)
        )
        return FactItem(
            type=item.get("type", "document"),
            text=str(text),
            metadata=item,
            source_id=item.get("id"),
        )

    # Handle string items
    if isinstance(item, str):
        return FactItem(
            type="text",
            text=item,
            metadata={},
        )

    return None


def _evidence_to_facts(evidence: str) -> list[FactItem]:
    """
    Best-effort parser for pack_context() output.

    Expected block format:
      [technology] RAG: RAG\\nИспользуется в: ...
    """
    text = (evidence or "").strip()
    if not text:
        return []

    facts: list[FactItem] = []
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        b = (block or "").strip()
        if not b:
            continue
        m = re.match(
            r"^\[(?P<type>[^\]]+)\]\s*(?P<title>[^:]+)\s*:\s*(?P<body>.*)$",
            b,
            flags=re.DOTALL,
        )
        if m:
            fact_type = (m.group("type") or "text").strip()
            title = (m.group("title") or "").strip()
            body = (m.group("body") or "").strip()
            facts.append(
                FactItem(
                    type=fact_type,
                    text=body or title or b,
                    metadata={"name": title} if title else {},
                    source_id=None,
                )
            )
        else:
            facts.append(
                FactItem(
                    type="text",
                    text=b,
                    metadata={},
                    source_id=None,
                )
            )
    return facts
