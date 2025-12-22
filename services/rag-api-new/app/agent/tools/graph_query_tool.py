"""
Graph Query Tool - wrapper for graph-based retrieval.

Executes structured queries against the knowledge graph.
Supports V3 filters: tech_category, scope, company_id, project_id.
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem, IntentV2

logger = logging.getLogger(__name__)


# Mapping from IntentV2 to legacy Intent enum values
_INTENT_MAPPING = {
    IntentV2.CURRENT_JOB: "current_job",
    IntentV2.PROJECT_DETAILS: "project_details",
    IntentV2.PROJECT_ACHIEVEMENTS: "achievements",
    IntentV2.PROJECT_TECH_STACK: "technologies",
    IntentV2.TECHNOLOGY_USAGE: "technologies",
    IntentV2.EXPERIENCE_SUMMARY: "experience",
    IntentV2.TECHNOLOGY_OVERVIEW: "technologies",
    IntentV2.CONTACTS: "contacts",
    IntentV2.GENERAL_UNSTRUCTURED: "general",
}


def execute_graph_query(
    intent: str,
    entity_id: str | None = None,
    tech_category: str | None = None,
    scope: str | None = None,
    company_id: str | None = None,
    project_id: str | None = None,
    limit: int = 20,
) -> tuple[list[FactItem], list[dict[str, Any]], bool, float]:
    """
    Execute a graph query and return structured facts.

    Args:
        intent: Query intent (from IntentV2 or legacy Intent)
        entity_id: Optional entity ID like "project:alor-broker"
        tech_category: Filter technologies by category from data (language/database/etc.)
        scope: Query scope level (global/company/project)
        company_id: Filter by company ID
        project_id: Filter by project ID
        limit: Maximum number of results

    Returns:
        Tuple of (facts, sources, found, confidence)
    """
    from ...graph.query import graph_query, graph_query_with_filters
    from ...rag.search_types import Intent

    # Parse entity_key from entity_id
    entity_key = None
    if entity_id:
        parts = entity_id.split(":", 1)
        if len(parts) == 2:
            entity_key = parts[1]
        else:
            entity_key = entity_id

    # Parse company/project keys from IDs
    company_key = None
    if company_id:
        parts = company_id.split(":", 1)
        company_key = parts[1] if len(parts) == 2 else company_id

    project_key = None
    if project_id:
        parts = project_id.split(":", 1)
        project_key = parts[1] if len(parts) == 2 else project_id

    # Convert intent string to Intent enum
    intent_lower = intent.lower()

    try:
        intent_enum = Intent(intent_lower)
    except ValueError:
        for iv2, legacy in _INTENT_MAPPING.items():
            if iv2.value == intent_lower or legacy == intent_lower:
                try:
                    intent_enum = Intent(legacy)
                    break
                except ValueError:
                    continue
        else:
            logger.warning("Unknown intent: %s, using GENERAL", intent)
            intent_enum = Intent.GENERAL

    logger.info(
        "graph_query: intent=%s, entity_key=%s, tech_category=%s, scope=%s, company=%s, project=%s",
        intent_enum.value,
        entity_key,
        tech_category,
        scope,
        company_key,
        project_key,
    )

    # Use filters if provided, otherwise use legacy query
    if tech_category or company_key or project_key:
        result = graph_query_with_filters(
            intent=intent_enum,
            entity_key=entity_key,
            tech_category=tech_category,
            company_key=company_key,
            project_key=project_key,
            limit=limit,
        )
    else:
        result = graph_query(intent_enum, entity_key)

    # Convert items to FactItem
    facts = []
    for item in result.items:
        fact = _item_to_fact(item, intent_enum)
        if fact:
            facts.append(fact)

    # Apply limit
    if limit and len(facts) > limit:
        facts = facts[:limit]

    return facts, result.sources, result.found, result.confidence


def _item_to_fact(item: Any, intent: Any) -> FactItem | None:
    """Convert a graph query item to FactItem."""
    if isinstance(item, dict):
        text = item.get("text")
        if not text:
            if item.get("technology") and item.get("project"):
                tech = item.get("technology")
                proj = item.get("project")
                comp = item.get("company_name")
                suffix = f" ({comp})" if comp else ""
                text = f"{tech} используется в проекте {proj}{suffix}"
            elif item.get("name") and any(k in item for k in ("description", "long_description", "domain", "period")):
                name = item.get("name")
                desc = item.get("description") or item.get("long_description") or ""
                domain = item.get("domain")
                period = item.get("period")
                parts = [str(name)]
                if domain:
                    parts.append(f"домен: {domain}")
                if period:
                    parts.append(f"период: {period}")
                if desc:
                    parts.append(str(desc))
                text = " — ".join([p for p in parts if p])
            elif item.get("company") or item.get("role"):
                company = item.get("company")
                role = item.get("role")
                period = item.get("period")
                start_date = item.get("start_date")
                summary = item.get("company_summary_md") or ""
                role_md = item.get("company_role_md") or ""
                parts = []
                if company and role:
                    parts.append(f"{company} — {role}")
                elif company:
                    parts.append(str(company))
                if period:
                    parts.append(str(period))
                elif start_date:
                    parts.append(f"с {start_date}")
                if summary:
                    parts.append(str(summary))
                if role_md:
                    parts.append(str(role_md))
                text = "\n".join([p for p in parts if p])
            else:
                text = item.get("achievement") or item.get("name") or item.get("description") or str(item)

        # Determine fact type
        if "achievement" in item:
            fact_type = "achievement"
        elif "name" in item and "category" in item:
            fact_type = "technology"
        elif item.get("technology") and item.get("project"):
            fact_type = "technology_usage"
        elif "company" in item or "role" in item:
            fact_type = "experience"
        elif "kind" in item and ("url" in item or "value" in item):
            fact_type = "contact"
        else:
            fact_type = intent.value if hasattr(intent, "value") else str(intent)

        return FactItem(
            type=fact_type,
            text=str(text),
            metadata=item,
            source_id=item.get("id") or item.get("source_id"),
        )

    elif isinstance(item, str):
        return FactItem(
            type="text",
            text=item,
            metadata={},
        )

    return None
