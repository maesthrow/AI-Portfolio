"""
Merge node for RAG agent.

Combines results from parallel retrieval (graph + search).
Deduplicates facts and merges sources.

This is the fan-in point after parallel retrieval.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.planner.schemas import FactItem, SourceInfo

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def merge_results_node(state: RAGState) -> dict:
    """
    Merge results from graph and search retrievers.

    Combines facts, deduplicates by source_id and text similarity,
    and merges source references.

    This is the fan-in point where parallel retrieval results are combined.
    Sources from both retrievers are converted from raw dicts to SourceInfo.

    Args:
        state: Current RAGState with graph_facts, search_facts,
               graph_sources, search_sources

    Returns:
        Partial state update with:
        - merged_facts: Combined and deduplicated facts
        - retrieval_found: Whether any facts were found
        - sources: Merged and deduplicated sources (as SourceInfo)
    """
    graph_facts: list[FactItem] = state.get("graph_facts", [])
    search_facts: list[FactItem] = state.get("search_facts", [])
    graph_sources: list[dict] = state.get("graph_sources", [])
    search_sources: list[dict] = state.get("search_sources", [])

    logger.info(
        f"Merge: graph_facts={len(graph_facts)}, search_facts={len(search_facts)}, "
        f"graph_sources={len(graph_sources)}, search_sources={len(search_sources)}"
    )

    # Combine all facts
    all_facts = graph_facts + search_facts

    # Deduplicate by source_id
    seen_source_ids: set[str] = set()
    seen_texts: set[str] = set()
    merged_facts: list[FactItem] = []

    for fact in all_facts:
        # Check source_id uniqueness
        if fact.source_id:
            if fact.source_id in seen_source_ids:
                continue
            seen_source_ids.add(fact.source_id)

        # Check text uniqueness (normalized)
        text_key = _normalize_text(fact.text)
        if text_key in seen_texts:
            continue
        if text_key:
            seen_texts.add(text_key)

        merged_facts.append(fact)

    # Combine and convert raw sources to SourceInfo
    all_raw_sources = graph_sources + search_sources
    seen_ids: set[str] = set()
    merged_sources: list[SourceInfo] = []

    for s in all_raw_sources:
        if not isinstance(s, dict):
            continue
        source_id = str(s.get("id", ""))
        if not source_id or source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        merged_sources.append(
            SourceInfo(
                id=source_id,
                label=str(s.get("label", s.get("id", ""))),
                type=s.get("type"),
            )
        )

    retrieval_found = len(merged_facts) > 0

    logger.info(
        f"Merge result: merged_facts={len(merged_facts)}, "
        f"sources={len(merged_sources)}, found={retrieval_found}"
    )

    return {
        "merged_facts": merged_facts,
        "retrieval_found": retrieval_found,
        "sources": merged_sources,
    }


def _normalize_text(text: str) -> str:
    """Normalize text for deduplication."""
    if not text:
        return ""
    # Lowercase, remove extra whitespace
    normalized = " ".join(text.lower().split())
    # Take first 100 chars for comparison
    return normalized[:100]
