"""
Tool Executor Node - executes tools selected by Planner.

Reads tool_calls from plan, executes each tool using the tool registry,
and collects results into merged_facts.

Replaces the parallel retrieval nodes (graph_retriever, search_retriever)
with a simpler sequential execution model.
"""
from __future__ import annotations

import logging
from typing import Any

from ..state import RAGState
from ..tools import execute_tool, is_valid_tool
from ..tools.schemas import ToolResult, TOOL_SEARCH_PORTFOLIO
from ..planner.schemas import FactItem

logger = logging.getLogger(__name__)


def tool_executor_node(state: RAGState) -> dict[str, Any]:
    """
    Execute tools from the plan and collect results.

    Steps:
    1. Read tool_calls from plan
    2. Execute each tool using tool_registry
    3. Merge results into facts and sources
    4. Handle fallback if no results found

    Args:
        state: Current RAG state with plan from Planner

    Returns:
        State update with merged_facts, sources, retrieval_found
    """
    plan = state.get("plan")
    question = state.get("question", "")
    validated_entities = state.get("validated_entities", {})

    if not plan:
        logger.warning("ToolExecutor: no plan available, using fallback search")
        return _execute_fallback(question, validated_entities)

    tool_calls = plan.tool_calls or []

    if not tool_calls:
        logger.warning("ToolExecutor: no tool_calls in plan, using fallback search")
        return _execute_fallback(question, validated_entities)

    logger.info(
        "ToolExecutor: executing %d tool calls",
        len(tool_calls),
    )

    all_facts: list[FactItem] = []
    all_sources: list[dict[str, Any]] = []
    all_evidence: list[str] = []  # Collect evidence_text from tools
    any_found = False
    max_confidence = 0.0

    # Execute each tool call
    for i, tc in enumerate(tool_calls):
        tool_name = tc.tool
        args = dict(tc.args)

        # Map legacy tool names to new tools
        tool_name = _map_tool_name(tool_name, args)

        if not is_valid_tool(tool_name):
            logger.warning(
                "ToolExecutor: unknown tool '%s', skipping",
                tool_name,
            )
            continue

        logger.info(
            "ToolExecutor: [%d/%d] executing '%s'",
            i + 1,
            len(tool_calls),
            tool_name,
        )

        # Execute tool
        result = execute_tool(tool_name, args)

        if result.error:
            logger.warning(
                "ToolExecutor: tool '%s' error: %s",
                tool_name,
                result.error,
            )
            continue

        # Collect results
        all_facts.extend(result.facts)
        all_sources.extend(result.sources)

        # Collect evidence_text from this tool (if any)
        if result.evidence_text:
            all_evidence.append(result.evidence_text)

        if result.found:
            any_found = True

        if result.confidence > max_confidence:
            max_confidence = result.confidence

        logger.info(
            "ToolExecutor: tool '%s' returned %d facts, found=%s",
            tool_name,
            len(result.facts),
            result.found,
        )

    # Deduplicate facts by source_id
    unique_facts = _deduplicate_facts(all_facts)

    # If no results and fallback enabled, try fallback search
    if not any_found and plan.fallback and plan.fallback.enabled:
        logger.info("ToolExecutor: no results, trying fallback search")
        fallback_result = _execute_fallback(question, validated_entities)

        # Merge fallback results
        unique_facts.extend(fallback_result.get("merged_facts", []))
        all_sources.extend(fallback_result.get("sources", []))
        any_found = fallback_result.get("retrieval_found", False)

        # Add fallback evidence
        fallback_evidence = fallback_result.get("evidence_text", "")
        if fallback_evidence:
            all_evidence.append(fallback_evidence)

    logger.info(
        "ToolExecutor: total %d unique facts, found=%s",
        len(unique_facts),
        any_found,
    )

    # Combine evidence from current request's tools only
    current_evidence = "\n\n".join(all_evidence) if all_evidence else ""

    return {
        "merged_facts": unique_facts,
        "sources": _deduplicate_sources(all_sources),
        "retrieval_found": any_found,
        # CRITICAL FIX: Set evidence_text to ONLY current request's data
        # This prevents state pollution from previous requests
        "evidence_text": current_evidence,
    }


def _map_tool_name(tool_name: str, args: dict[str, Any]) -> str:
    """
    Map legacy tool names to new specialized tools.

    Legacy tools:
    - graph_query_tool -> mapped based on intent
    - portfolio_search_tool -> search_portfolio

    Args:
        tool_name: Original tool name
        args: Tool arguments (may contain intent)

    Returns:
        New tool name
    """
    # Already new tool
    if tool_name in (
        "get_company_projects",
        "get_project_details",
        "get_technologies",
        "get_contacts",
        "search_portfolio",
    ):
        return tool_name

    # Map portfolio_search_tool
    if tool_name in ("portfolio_search_tool", "portfolio_search"):
        return "search_portfolio"

    # Map graph_query_tool based on intent
    if tool_name in ("graph_query_tool", "graph_query"):
        intent = args.get("intent", "").lower()

        # Company projects
        if intent in ("project_list", "project_details") and args.get("entity_id", "").startswith("company:"):
            return "get_company_projects"

        # Project details
        if intent in ("project_details", "project_tech_stack", "project_achievements"):
            return "get_project_details"

        # Technologies
        if intent in ("technology_overview", "technology_usage", "languages"):
            return "get_technologies"

        # Contacts - P0 FIX: route to get_contacts instead of search_portfolio
        if intent == "contacts":
            return "get_contacts"

        # Default to search
        return "search_portfolio"

    return tool_name


def _execute_fallback(
    question: str,
    validated_entities: dict[str, Any],
) -> dict[str, Any]:
    """
    Execute fallback search when primary tools fail.

    Args:
        question: Original question
        validated_entities: Validated company/project from session

    Returns:
        State update dict with merged_facts, sources, retrieval_found
    """
    company = validated_entities.get("company")
    project = validated_entities.get("project")

    args = {
        "query": question,
        "k": 8,
    }

    # Add filters from session context
    if company:
        args["company_filter"] = company
    if project:
        args["project_filter"] = project

    logger.info(
        "ToolExecutor fallback: search_portfolio query=%r, company=%s, project=%s",
        question[:50],
        company,
        project,
    )

    result = execute_tool(TOOL_SEARCH_PORTFOLIO, args)

    return {
        "merged_facts": result.facts,
        "sources": result.sources,
        "retrieval_found": result.found,
        "evidence_text": result.evidence_text,
    }


def _deduplicate_facts(facts: list[FactItem]) -> list[FactItem]:
    """
    Deduplicate facts by source_id.

    Keeps first occurrence of each unique source_id.
    Facts without source_id are always kept.

    Args:
        facts: List of facts

    Returns:
        Deduplicated list
    """
    seen_ids: set[str] = set()
    unique: list[FactItem] = []

    for fact in facts:
        if fact.source_id:
            if fact.source_id in seen_ids:
                continue
            seen_ids.add(fact.source_id)

        unique.append(fact)

    return unique


def _deduplicate_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Deduplicate sources by id.

    Args:
        sources: List of source dicts

    Returns:
        Deduplicated list
    """
    seen_ids: set[str] = set()
    unique: list[dict[str, Any]] = []

    for source in sources:
        source_id = source.get("id")
        if source_id:
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

        unique.append(source)

    return unique
