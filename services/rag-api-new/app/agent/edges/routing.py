"""
Conditional edge routing functions for RAG agent.

These functions determine which node to execute next
based on the current state.

Simplified 2-LLM architecture:
1. route_scope - Routes based on scope_category (portfolio -> planner, other -> simple_llm)

Legacy routers (route_needs_search, route_answer, route_grounding) have been REMOVED
as they were part of the deprecated 4-LLM architecture.
"""
from __future__ import annotations

import logging
from typing import Literal

from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def route_scope(state: RAGState) -> Literal["planner", "simple_llm"]:
    """
    Route based on scope classification.

    For portfolio questions → planner (full RAG pipeline)
    For small_talk/off_topic/harmful → simple_llm (single LLM response)

    Args:
        state: Current RAGState with scope_category

    Returns:
        "planner" for portfolio questions
        "simple_llm" for non-portfolio questions
    """
    scope_category = state.get("scope_category", "portfolio")

    if scope_category == "portfolio":
        logger.info("RouteScope: portfolio → planner")
        return "planner"
    else:
        logger.info(f"RouteScope: {scope_category} → simple_llm")
        return "simple_llm"
