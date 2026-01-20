"""
State Cleanup Node - resets per-request fields at pipeline start.

This node prevents state pollution between requests in the same session.
LangGraph's MemorySaver persists ALL state fields, including intermediate
data like evidence_text. Without explicit cleanup, data from previous
requests can leak into current responses.

Example issue fixed:
- Request 1: "Что за проект AI-Portfolio?" -> evidence_text = "AI-Portfolio description..."
- Request 2: "Контакты?" -> Without cleanup, evidence_text still contains project data
- Result: Contacts response contaminated with project information

This node MUST be the first node in the pipeline after entry.
"""
from __future__ import annotations

import logging
from typing import Any

from ..state import RAGState, get_cleanup_state

logger = logging.getLogger(__name__)


def state_cleanup_node(state: RAGState) -> dict[str, Any]:
    """
    Clear all per-request fields to prevent state pollution.

    This node runs at the start of each request pipeline.
    It resets all intermediate state fields while preserving:
    - messages (conversation history)
    - session_id (session identifier)
    - last_company, last_project, etc. (session context)

    Args:
        state: Current RAG state (may contain stale data from previous request)

    Returns:
        State update with all per-request fields reset to defaults
    """
    # Get the cleanup state (all per-request fields set to defaults)
    cleanup = get_cleanup_state()

    # Log what we're clearing (for debugging state pollution issues)
    stale_evidence = state.get("evidence_text", "")
    stale_facts_count = len(state.get("merged_facts", []))

    if stale_evidence or stale_facts_count:
        logger.info(
            "StateCleanup: clearing stale data - evidence_text=%d chars, merged_facts=%d items",
            len(stale_evidence),
            stale_facts_count,
        )

    logger.debug("StateCleanup: reset %d per-request fields", len(cleanup))

    return cleanup
