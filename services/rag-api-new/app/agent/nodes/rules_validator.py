"""
Rules Validator Node - validates and augments Planner output.

Applies deterministic rules to:
1. Extract entities from question text (backup if Planner missed them)
2. Resolve reference patterns ("там", "в ней") using session context
3. Validate tool_calls from Planner
4. Inject session context (last_company, last_project) into tool params

Part of the simplified 2-LLM architecture.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..state import RAGState
from ..planner.schemas_v3 import QueryPlanV3, ToolCallV3

logger = logging.getLogger(__name__)


# === Entity Patterns ===
# These patterns are loaded at module init and can be extended dynamically

COMPANY_PATTERNS: dict[str, list[str]] = {
    "aston": ["aston", "астон", "астоне", "астона", "астоном"],
    "spargo": ["spargo", "спарго", "спарге", "спарга", "spargo-technologies", "спарго технологии"],
    "alor": ["alor", "алор", "алоре", "алора"],
    "freelance": ["freelance", "фриланс", "фрилансе", "самозанят"],
}

PROJECT_PATTERNS: dict[str, list[str]] = {
    "t2": ["t2", "tier2", "tier-2", "т2", "тиер2"],
    "ai-portfolio": ["ai-portfolio", "ai portfolio", "портфолио", "portfolio"],
    "alor-broker": ["alor-broker", "alor broker", "алор брокер", "alor"],
    "hyperkeeper": ["hyperkeeper", "hyper-keeper", "hyper keeper", "гиперкипер"],
}

# Reference patterns that indicate anaphora (reference to previous entity)
REFERENCE_PATTERNS = [
    "там", "туда", "оттуда", "в ней", "в нём", "в нем",
    "этой", "этого", "этом", "этим",
    "той", "того", "том", "тем",
    "какой там", "что там", "какие там",
    "а там", "а что там",
]


def rules_validator_node(state: RAGState) -> dict[str, Any]:
    """
    Validate and augment Planner output with session context.

    Steps:
    1. Extract entities from question using regex patterns
    2. Check for reference patterns and resolve using session context
    3. Validate tool_calls from Planner
    4. Update tool_calls with validated entities

    Args:
        state: Current RAG state with plan from Planner

    Returns:
        State update with validated_entities and possibly updated plan
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

    # 1. Extract entities from question text
    extracted_company = extract_company(question)
    extracted_project = extract_project(question)

    logger.debug(
        "Extracted: company=%s, project=%s",
        extracted_company,
        extracted_project,
    )

    # 2. Check for reference patterns and resolve using session context
    has_reference = has_reference_pattern(question)

    if has_reference:
        logger.info("Reference pattern detected in question")

        # Resolve company reference
        if not extracted_company and last_company:
            extracted_company = last_company
            logger.info("Resolved company reference to: %s", extracted_company)

        # Resolve project reference
        if not extracted_project and last_project:
            extracted_project = last_project
            logger.info("Resolved project reference to: %s", extracted_project)

    # Build validated_entities dict
    validated_entities = {
        "company": extracted_company,
        "project": extracted_project,
        "from_session": has_reference and (extracted_company == last_company or extracted_project == last_project),
    }

    # 3. Validate and update tool_calls if plan exists
    if plan:
        updated_tool_calls = _validate_tool_calls(
            plan.tool_calls,
            validated_entities,
            question,
        )

        # Create updated plan
        if updated_tool_calls != plan.tool_calls:
            logger.info("Updated tool_calls with validated entities")

            # Update plan with new tool_calls
            # Note: We can't directly modify Pydantic model, so we create a new one
            plan_dict = plan.model_dump()
            plan_dict["tool_calls"] = [tc.model_dump() for tc in updated_tool_calls]

            # Also update scope if we have company context
            if validated_entities.get("company") and plan_dict.get("scope"):
                plan_dict["scope"]["company_id"] = f"company:{validated_entities['company']}"
                plan_dict["scope"]["level"] = "company"

            try:
                updated_plan = QueryPlanV3.model_validate(plan_dict)
                return {
                    "plan": updated_plan,
                    "validated_entities": validated_entities,
                }
            except Exception as e:
                logger.warning("Failed to update plan: %s", e)

    return {
        "validated_entities": validated_entities,
    }


def extract_company(text: str) -> str | None:
    """
    Extract company slug from text using pattern matching.

    Args:
        text: Question text

    Returns:
        Company slug if found, None otherwise
    """
    if not text:
        return None

    text_lower = text.lower()

    for slug, patterns in COMPANY_PATTERNS.items():
        for pattern in patterns:
            # Use word boundary matching to avoid partial matches
            if re.search(rf"\b{re.escape(pattern)}\b", text_lower):
                return slug

            # Also check without word boundaries for Russian morphology
            if pattern in text_lower:
                return slug

    return None


def extract_project(text: str) -> str | None:
    """
    Extract project slug from text using pattern matching.

    Args:
        text: Question text

    Returns:
        Project slug if found, None otherwise
    """
    if not text:
        return None

    text_lower = text.lower()

    for slug, patterns in PROJECT_PATTERNS.items():
        for pattern in patterns:
            # Use word boundary matching
            if re.search(rf"\b{re.escape(pattern)}\b", text_lower):
                return slug

            # Also check without word boundaries
            if pattern in text_lower:
                return slug

    return None


def has_reference_pattern(text: str) -> bool:
    """
    Check if text contains reference patterns (anaphora).

    These patterns indicate the user is referring to a previously
    mentioned entity ("там", "в ней", "этой компании", etc.)

    Args:
        text: Question text

    Returns:
        True if reference pattern found
    """
    if not text:
        return False

    text_lower = text.lower()

    for pattern in REFERENCE_PATTERNS:
        if pattern in text_lower:
            return True

    return False


def _validate_tool_calls(
    tool_calls: list[ToolCallV3],
    validated_entities: dict[str, Any],
    question: str,
) -> list[ToolCallV3]:
    """
    Validate and update tool_calls with session context.

    - Injects company_filter into search_portfolio
    - Adds company_name to get_company_projects if missing
    - Adds project_name to get_project_details if missing

    Args:
        tool_calls: Original tool calls from Planner
        validated_entities: Validated company/project from rules
        question: Original question

    Returns:
        Updated list of ToolCallV3
    """
    company = validated_entities.get("company")
    project = validated_entities.get("project")

    updated_calls = []

    for tc in tool_calls:
        tool_name = tc.tool
        args = dict(tc.args)  # Make a copy

        # Inject company context
        if company:
            if tool_name == "search_portfolio":
                # Add company_filter if not present
                if "company_filter" not in args:
                    args["company_filter"] = company
                    logger.debug("Injected company_filter=%s into search_portfolio", company)

            elif tool_name == "get_company_projects":
                # Add company_name if not present
                if not args.get("company_name"):
                    args["company_name"] = company
                    logger.debug("Injected company_name=%s into get_company_projects", company)

        # Inject project context
        if project:
            if tool_name == "get_project_details":
                # Add project_name if not present
                if not args.get("project_name"):
                    args["project_name"] = project
                    logger.debug("Injected project_name=%s into get_project_details", project)

            elif tool_name == "get_technologies":
                # Add project_name if not present and no category specified
                if not args.get("project_name") and not args.get("category"):
                    args["project_name"] = project
                    logger.debug("Injected project_name=%s into get_technologies", project)

        # Create updated ToolCallV3
        updated_call = ToolCallV3(tool=tool_name, args=args)
        updated_calls.append(updated_call)

    return updated_calls


# === Dynamic Pattern Loading ===

def load_patterns_from_graph() -> None:
    """
    Load company and project patterns from knowledge graph.

    Called at startup to populate patterns with actual data.
    This allows patterns to be dynamically updated when new
    companies/projects are added.
    """
    try:
        from ...graph.store import get_graph_store
        from ...graph.schema import NodeType

        store = get_graph_store()

        # Load companies
        companies = store.get_nodes_by_type(NodeType.COMPANY)
        for c in companies:
            slug = c.slug.lower()
            if slug not in COMPANY_PATTERNS:
                COMPANY_PATTERNS[slug] = [slug, c.name.lower()]

        # Load projects
        projects = store.get_nodes_by_type(NodeType.PROJECT)
        for p in projects:
            slug = p.slug.lower()
            if slug not in PROJECT_PATTERNS:
                PROJECT_PATTERNS[slug] = [slug, p.name.lower()]

        logger.info(
            "Loaded %d company patterns and %d project patterns from graph",
            len(COMPANY_PATTERNS),
            len(PROJECT_PATTERNS),
        )

    except Exception as e:
        logger.warning("Failed to load patterns from graph: %s", e)
