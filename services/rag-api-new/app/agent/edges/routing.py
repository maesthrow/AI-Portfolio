"""
Conditional edge routing functions for RAG agent.

These functions determine which node to execute next
based on the current state.

Available routers:
1. route_scope - Routes based on scope_category
2. route_needs_search - Routes based on critic's additional search decision
3. route_answer - Routes to deterministic or LLM answer
4. route_grounding - Routes based on grounding verification result
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


def route_needs_search(
    state: RAGState,
) -> Literal["additional_search", "normalizer"]:
    """
    Route based on critic's additional search decision.

    If critic determined more search is needed → additional_search
    Otherwise → normalizer (continue to answer generation)

    Args:
        state: Current RAGState with needs_additional_search

    Returns:
        "additional_search" if more search needed
        "normalizer" if results are sufficient
    """
    needs_search = state.get("needs_additional_search", False)

    if needs_search:
        logger.info("RouteNeedsSearch: needs additional search")
        return "additional_search"
    else:
        logger.info("RouteNeedsSearch: results sufficient → normalizer")
        return "normalizer"


def route_answer(
    state: RAGState,
) -> Literal["answer_deterministic", "answer_llm"]:
    """
    Route to appropriate answer generation node.

    Deterministic answers for:
    - Empty facts (not found response)
    - contacts intent

    LLM answers for:
    - Complex intents requiring natural language
    - project_details, experience_summary, technology_usage, etc.

    Args:
        state: Current RAGState with normalized_facts and plan

    Returns:
        "answer_deterministic" for simple/empty cases
        "answer_llm" for complex cases
    """
    normalized_facts = state.get("normalized_facts", [])
    plan = state.get("plan")

    # Empty results → deterministic "not found"
    if not normalized_facts:
        logger.info("RouteAnswer: no facts → answer_deterministic")
        return "answer_deterministic"

    # Check intent for deterministic path
    if plan and plan.intents:
        intent = plan.intents[0].value

        # Only contacts can be answered deterministically
        if intent == "contacts":
            logger.info(f"RouteAnswer: {intent} → answer_deterministic")
            return "answer_deterministic"

    logger.info("RouteAnswer: complex intent → answer_llm")
    return "answer_llm"


def route_grounding(
    state: RAGState,
) -> Literal["output", "rewrite"]:
    """
    Route based on grounding verification result.

    accept → output (answer is grounded, proceed to output)
    rewrite/refuse → rewrite (need to fix hallucinations)

    Args:
        state: Current RAGState with grounding_action

    Returns:
        "output" if answer is accepted
        "rewrite" if answer needs fixing
    """
    grounding_action = state.get("grounding_action", "accept")

    if grounding_action == "accept":
        logger.info("RouteGrounding: accept → output")
        return "output"
    else:
        logger.info(f"RouteGrounding: {grounding_action} → rewrite")
        return "rewrite"
