"""
Normalizer node for RAG agent.

Applies deterministic filtering rules to facts based on:
- Intent (technology_overview, technology_usage, etc.)
- TechFilter (category, tags_any, strict mode)

This is a deterministic node (no LLM call).
Eliminates hallucinations like "MySQL probably" by strict filtering.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.normalizer.normalizer import normalize_facts
from app.agent.planner.schemas import FactItem

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def normalizer_node(state: RAGState) -> dict:
    """
    Apply deterministic normalization rules to facts.

    Rules applied:
    - technology_overview + category=X → only X-category technologies
    - technology_usage → only technology usage facts
    - experience_summary → prioritize experience facts
    - Limit application to respect max_items

    Args:
        state: Current RAGState with merged_facts and plan

    Returns:
        Partial state update with:
        - normalized_facts: Filtered FactBundleItem list
        - removed_facts_count: Number of facts removed
        - normalization_rules_applied: List of applied rules
    """
    merged_facts = state.get("merged_facts", [])
    plan = state.get("plan")

    if not merged_facts:
        logger.info("Normalizer: no facts to normalize")
        return {
            "normalized_facts": [],
            "removed_facts_count": 0,
            "normalization_rules_applied": [],
        }

    # Get intent and filters from plan
    intent = "general_unstructured"
    tech_filter = None
    max_items = 20

    if plan:
        if plan.intents:
            intent = plan.intents[0]
        tech_filter = plan.tech_filter
        if plan.limits:
            max_items = plan.limits.max_items

    logger.info(
        f"Normalizer processing: facts={len(merged_facts)}, "
        f"intent={intent}, tech_filter={tech_filter}"
    )

    # Apply normalization
    result = normalize_facts(
        facts=merged_facts,
        intent=intent,
        tech_filter=tech_filter,
        max_items=max_items,
    )

    logger.info(
        f"Normalizer result: normalized={len(result.filtered_facts)}, "
        f"removed={result.removed_count}, rules={result.rules_applied}"
    )

    return {
        "normalized_facts": result.filtered_facts,
        "removed_facts_count": result.removed_count,
        "normalization_rules_applied": result.rules_applied,
    }
