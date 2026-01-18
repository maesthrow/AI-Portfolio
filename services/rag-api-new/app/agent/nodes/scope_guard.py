"""
ScopeGuard node for RAG agent.

Classifies user question into categories:
- portfolio: Questions about Dmitry's portfolio, projects, experience
- small_talk: Greetings, thanks, etc.
- off_topic: Unrelated questions (fairy tales, weather, etc.)
- harmful: Potentially harmful requests

This is a deterministic node (no LLM call).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.scope_guard.scope_guard import get_scope_guard

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def scope_guard_node(state: RAGState) -> dict:
    """
    Classify user question into scope categories.

    This is the entry point of the graph.
    Uses pattern matching for fast, deterministic classification.

    Args:
        state: Current RAGState with question

    Returns:
        Partial state update with:
        - in_scope: Whether question is about portfolio
        - scope_category: "portfolio" | "small_talk" | "off_topic" | "harmful"
        - scope_reason: Reason for classification (for debugging)
        - suggested_prompts: Suggested portfolio questions (if out of scope)
    """
    question = state.get("question", "")

    logger.debug(f"ScopeGuard evaluating: {question[:100]}...")

    scope_guard = get_scope_guard()
    decision = scope_guard.evaluate(question)

    logger.info(
        f"ScopeGuard decision: category={decision.category}, "
        f"in_scope={decision.in_scope}, reason={decision.reason}"
    )

    return {
        "in_scope": decision.in_scope,
        "scope_category": decision.category,
        "scope_reason": decision.reason,
        "suggested_prompts": decision.suggested_prompts,
    }
