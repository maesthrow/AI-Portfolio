"""
Contact Tools - specialized tool for contact information queries.

Provides get_contacts function for retrieving contact information
from the knowledge graph.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem
from .schemas import ToolResult, TOOL_GET_CONTACTS

logger = logging.getLogger(__name__)


def get_contacts(
    kind: str | None = None,
) -> ToolResult:
    """
    Get contact information.

    Returns all contacts or filters by kind (email, telegram, github, etc.).

    Args:
        kind: Optional contact kind filter (email, telegram, github, linkedin, hh, leetcode)

    Returns:
        ToolResult with contact facts

    Examples:
        - "как связаться" -> get_contacts()
        - "есть гитхаб?" -> get_contacts(kind="github")
        - "telegram" -> get_contacts(kind="telegram")
    """
    from ...graph.query import _contacts_query

    logger.info("get_contacts: kind=%s", kind)

    try:
        result = _contacts_query()

        # Convert items to FactItem
        facts = []
        for item in result.items:
            fact = _item_to_fact(item)
            if fact:
                # Apply kind filter if specified
                if kind:
                    item_kind = (item.get("kind") or "").lower()
                    if kind.lower() not in item_kind and item_kind not in kind.lower():
                        continue
                facts.append(fact)

        logger.info(
            "get_contacts: found %d contacts (filtered by kind=%s)",
            len(facts),
            kind,
        )

        return ToolResult(
            facts=facts,
            sources=result.sources,
            found=len(facts) > 0,
            confidence=result.confidence if facts else 0.0,
            tool_name=TOOL_GET_CONTACTS,
            params={"kind": kind},
        )

    except Exception as e:
        logger.error("get_contacts error: %s", e)
        return ToolResult(
            facts=[],
            sources=[],
            found=False,
            confidence=0.0,
            tool_name=TOOL_GET_CONTACTS,
            params={"kind": kind},
            error=str(e),
        )


def _item_to_fact(item: dict[str, Any]) -> FactItem | None:
    """Convert a contact item to FactItem."""
    if not isinstance(item, dict):
        return None

    kind = item.get("kind")
    label = item.get("label")
    value = item.get("value")
    url = item.get("url")

    if not kind:
        return None

    # Build text representation
    text_parts = [f"{label or kind}"]
    if url:
        text_parts.append(url)
    elif value:
        text_parts.append(value)

    text = ": ".join(text_parts)

    return FactItem(
        type="contact",
        text=text,
        metadata={
            "kind": kind,
            "label": label,
            "value": value,
            "url": url,
        },
        source_id=f"contact:{kind}",
    )
