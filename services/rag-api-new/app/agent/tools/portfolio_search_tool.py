"""
Portfolio Search Tool - wrapper for hybrid retrieval.

Executes full-text search with semantic and BM25 ranking.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem

logger = logging.getLogger(__name__)


def execute_portfolio_search(
    query: str,
    k: int = 8,
    allowed_types: list[str] | None = None,
) -> tuple[list[FactItem], list[dict[str, Any]], bool, float, str]:
    """
    Execute a portfolio search and return facts.

    Args:
        query: Search query
        k: Number of results to return
        allowed_types: Optional list of document types to filter

    Returns:
        Tuple of (facts, sources, found, confidence, evidence_text)
    """
    from ...rag.search import portfolio_search

    logger.info(
        "portfolio_search: query=%r, k=%d, types=%s",
        query[:50],
        k,
        allowed_types,
    )

    # Execute search
    result = portfolio_search(question=query, k=k)

    # Convert items to FactItem
    facts = []
    for item in result.items:
        fact = _item_to_fact(item, result.intent)
        if fact:
            facts.append(fact)

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
