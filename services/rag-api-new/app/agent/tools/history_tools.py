"""
History Tools - tool for work history queries.

Provides get_work_history function for retrieving
chronological list of companies Dmitry worked at.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from ..planner.schemas import FactItem
from .schemas import ToolResult, TOOL_GET_WORK_HISTORY

logger = logging.getLogger(__name__)


def get_work_history(
    include_current: bool = False,
    order: Literal["chronological_asc", "chronological_desc"] = "chronological_desc",
) -> ToolResult:
    """
    Get work history (list of companies).

    Returns chronological list of companies with roles and periods.
    Used for questions like "где работал ранее", "до этого где работал".

    Args:
        include_current: Whether to include current workplace
        order: Sort order - "chronological_desc" (latest first) or "chronological_asc"

    Returns:
        ToolResult with company history

    Examples:
        - "где работал ранее" -> get_work_history(include_current=False)
        - "вся история работы" -> get_work_history(include_current=True)
    """
    from ...graph.query import _work_history_query

    logger.info(
        "get_work_history: include_current=%s, order=%s",
        include_current,
        order,
    )

    try:
        result = _work_history_query(include_current, order)

        facts = []
        for item in result.items:
            fact = _item_to_fact(item)
            if fact:
                facts.append(fact)

        logger.info(
            "get_work_history: found %d companies (include_current=%s)",
            len(facts),
            include_current,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=result.found,
            confidence=result.confidence,
            tool_name=TOOL_GET_WORK_HISTORY,
            params={
                "include_current": include_current,
                "order": order,
            },
        )

    except Exception as e:
        logger.error("get_work_history error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_WORK_HISTORY,
            params={"include_current": include_current, "order": order},
            error=str(e),
        )


def _item_to_fact(item: dict[str, Any]) -> FactItem | None:
    """Convert work history item to FactItem."""
    if not isinstance(item, dict):
        return None

    company = item.get("company")
    if not company:
        return None

    role = item.get("role") or ""
    period = item.get("period") or ""
    is_current = item.get("is_current", False)

    # Human-friendly text format
    text_parts = [company]
    if role:
        text_parts.append(f"— {role}")
    if period:
        text_parts.append(f"({period})")
    if is_current:
        text_parts.append("[текущее место]")

    text = " ".join(text_parts)

    return FactItem(
        type="experience",
        text=text,
        metadata={
            "company_name": company,
            "company_slug": item.get("company_slug"),
            "role": role,
            "period": period,
            "start_date": item.get("start_date"),
            "end_date": item.get("end_date"),
            "is_current": is_current,
        },
        source_id=item.get("company_slug"),
    )
