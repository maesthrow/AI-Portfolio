"""
Rules Validator Node - validates Planner output and computes intents.

SIMPLIFIED VERSION (after systemic fixes):
- Planner now receives EXPLICIT session context, so it should choose correct tools
- This node only: computes intents from tools, injects args as backup safety net

Part of the simplified 2-LLM architecture.
"""
from __future__ import annotations

import logging
from typing import Any

from ..state import RAGState
from ..planner.schemas_v3 import QueryPlanV3, ToolCallV3, IntentV3

logger = logging.getLogger(__name__)


# === Intent Derivation from Tool ===
# SYSTEMIC SOLUTION: compute intent deterministically from tool_name + args
# This removes LLM confusion between intents and tool names

TOOL_TO_INTENT_MAP: dict[str, str] = {
    "get_company_projects": "project_list",
    "get_project_details": "project_details",
    "get_technologies": "technology_overview",
    "get_contacts": "contacts",
    "search_portfolio": "general_unstructured",
    # Legacy tools
    "graph_query_tool": "general_unstructured",
    "portfolio_search_tool": "general_unstructured",
    # New tools (ТЗ v3)
    "get_work_history": "work_history",
    "get_company_achievements": "company_achievements",
    "get_project_achievements": "project_achievements",
    "get_project_summary": "entity_definition",
    "get_company_summary": "entity_definition",
}

# Keyword triggers for intent refinement (ТЗ v3 section 7)
ENTITY_DEFINITION_KEYWORDS = ["что такое", "что за", "расскажи о", "опиши", "объясни"]
WORK_HISTORY_KEYWORDS = ["ранее", "до этого", "предыдущ", "раньше", "прошл", "до aston", "до астон"]
ACHIEVEMENTS_KEYWORDS = ["достижен", "результат", "impact", "чего добился", "успех", "улучшил", "ускорил", "сократил"]
# NOTE: "чем занимался в [company]" is handled by Planner (rule 5 + example).
# These keywords are for search_portfolio fallback refinement only.
COMPANY_DETAILS_KEYWORDS = ["чем занимался в компании", "что делал в компании", "задачи в"]


def derive_intent_from_tool(tool_name: str, args: dict, question: str = "") -> str:
    """
    Derive intent deterministically from tool name, arguments, and question.

    SYSTEMIC SOLUTION: instead of asking LLM to output both tool and intent
    (which leads to confusion), we compute intent from the chosen tool.

    NOTE: For search_portfolio, we need question analysis because it's a
    GENERIC tool that can search different types of information. The intent
    determines how Normalizer filters results.

    This is NOT a hack - it's necessary semantics for generic search.

    Args:
        tool_name: Name of the tool being called
        args: Tool arguments
        question: Original question (for search_portfolio intent refinement)

    Returns:
        Valid intent string that matches IntentV3 enum values
    """
    intent = TOOL_TO_INTENT_MAP.get(tool_name, "general_unstructured")

    # Refinement based on args
    if tool_name == "get_technologies":
        if args.get("project_name"):
            intent = "project_tech_stack"
        # category → technology_overview (default)

    # For search_portfolio: determine WHAT TYPE of info user wants
    # This is necessary because search_portfolio is a generic tool
    if tool_name == "search_portfolio" and question:
        q_lower = question.lower()

        # === NEW: Entity definition keywords (ТЗ v3) ===
        if any(kw in q_lower for kw in ENTITY_DEFINITION_KEYWORDS):
            intent = "entity_definition"

        # === NEW: Work history keywords (ТЗ v3) ===
        elif any(kw in q_lower for kw in WORK_HISTORY_KEYWORDS):
            intent = "work_history"

        # === NEW: Achievements keywords (ТЗ v3) ===
        elif any(kw in q_lower for kw in ACHIEVEMENTS_KEYWORDS):
            # Determine company or project achievements based on context
            if args.get("company_filter"):
                intent = "company_achievements"
            elif args.get("project_filter"):
                intent = "project_achievements"
            else:
                # Default to company_achievements if company mentioned in question
                company_names = ["aston", "астон", "spargo", "спарго", "alor", "алор", "t-bank"]
                if any(c in q_lower for c in company_names):
                    intent = "company_achievements"
                else:
                    intent = "project_achievements"

        # === NEW: Company details keywords (ТЗ v3) ===
        elif any(kw in q_lower for kw in COMPANY_DETAILS_KEYWORDS):
            intent = "company_details"

        # Project-related keywords → project_list
        elif any(kw in q_lower for kw in ["проект", "project", "ml-проект", "rag-проект", "cv-проект"]):
            intent = "project_list"

        # Current job keywords → current_job
        elif any(kw in q_lower for kw in ["сейчас работа", "текущ", "current", "где работает"]):
            intent = "current_job"

        # Technology usage keywords → technology_usage
        elif any(kw in q_lower for kw in ["где применял", "где использовал", "опыт с"]):
            intent = "technology_usage"

        # Experience keywords → experience_summary
        elif any(kw in q_lower for kw in ["опыт работы", "experience", "карьер"]):
            intent = "experience_summary"

    logger.debug("Derived intent '%s' from tool '%s'", intent, tool_name)
    return intent


def rules_validator_node(state: RAGState) -> dict[str, Any]:
    """
    Validate Planner output and compute intents from tools.

    SIMPLIFIED after systemic fix:
    - Planner now receives explicit session context (last_company, last_project)
    - Planner should choose correct tool with correct args
    - This node only:
      1. Computes intents from tool_calls (systemic solution)
      2. Injects session context into args as backup safety net

    Args:
        state: Current RAG state with plan from Planner

    Returns:
        State update with computed intents and validated plan
    """
    plan = state.get("plan")
    question = state.get("question", "")
    last_company = state.get("last_company")
    last_project = state.get("last_project")

    logger.info(
        "RulesValidator: question=%r, last_company=%s, last_project=%s",
        question[:50] if question else "",
        last_company,
        last_project,
    )

    if not plan:
        return {}

    # === STEP 1: Compute intents from tool_calls (SYSTEMIC SOLUTION) ===
    # This removes dependency on LLM outputting correct intents
    derived_intents = []
    for tc in plan.tool_calls:
        intent_str = derive_intent_from_tool(tc.tool, tc.args, question)
        try:
            derived_intents.append(IntentV3(intent_str))
        except ValueError:
            derived_intents.append(IntentV3.GENERAL_UNSTRUCTURED)

    # Remove duplicates while preserving order
    seen = set()
    unique_intents = []
    for intent in derived_intents:
        if intent not in seen:
            seen.add(intent)
            unique_intents.append(intent)

    # === STEP 2: Safety net - inject session context into args if missing ===
    # Planner SHOULD have done this, but we double-check as backup
    updated_tool_calls = _ensure_session_context(
        plan.tool_calls,
        last_company,
        last_project,
    )

    # === STEP 3: Build updated plan ===
    old_intents = [i.value for i in plan.intents] if plan.intents else []
    new_intents = [i.value for i in unique_intents]

    if old_intents != new_intents:
        logger.info("Computed intents: %s (was: %s)", new_intents, old_intents)

    plan_dict = plan.model_dump()
    plan_dict["tool_calls"] = [tc.model_dump() for tc in updated_tool_calls]
    plan_dict["intents"] = new_intents

    try:
        updated_plan = QueryPlanV3.model_validate(plan_dict)
        return {"plan": updated_plan}
    except Exception as e:
        logger.warning("Failed to update plan: %s", e)
        return {}


def _ensure_session_context(
    tool_calls: list[ToolCallV3],
    last_company: str | None,
    last_project: str | None,
) -> list[ToolCallV3]:
    """
    Safety net: inject session context into tool args if Planner missed them.

    IMPORTANT: Only for tools that REQUIRE a specific entity:
    - get_company_projects REQUIRES company_name
    - get_project_details REQUIRES project_name

    DO NOT inject filters into search_portfolio - Planner decides if filtering is needed.
    General questions should search globally, not be filtered by stale context.

    Args:
        tool_calls: Tool calls from Planner
        last_company: Last company from session
        last_project: Last project from session

    Returns:
        Tool calls with session context injected where missing
    """
    updated_calls = []

    for tc in tool_calls:
        tool_name = tc.tool
        args = dict(tc.args)

        # Inject company ONLY for tools that require it
        if last_company:
            if tool_name == "get_company_projects" and not args.get("company_name"):
                args["company_name"] = last_company
                logger.info("Safety net: added company_name=%s to %s", last_company, tool_name)
            # NOTE: Do NOT add company_filter to search_portfolio automatically!
            # Planner decides if filtering is needed based on question context.

        # Inject project ONLY for tools that require it
        if last_project:
            if tool_name == "get_project_details" and not args.get("project_name"):
                args["project_name"] = last_project
                logger.info("Safety net: added project_name=%s to %s", last_project, tool_name)

            elif tool_name == "get_technologies" and not args.get("project_name") and not args.get("category"):
                # Only if neither project_name nor category specified
                args["project_name"] = last_project
                logger.info("Safety net: added project_name=%s to %s", last_project, tool_name)
            # NOTE: Do NOT add project_filter to search_portfolio automatically!

        updated_calls.append(ToolCallV3(tool=tool_name, args=args))

    return updated_calls
