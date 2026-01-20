"""
Planner node for RAG agent.

Uses LLM to generate QueryPlanV3 from user question.
This is the first LLM call in the portfolio pipeline.

SYSTEMIC FIX: Uses EntityExtractor to deterministically extract
entities BEFORE calling LLM. This removes the burden from LLM
to parse questions and decide if explicit entities override context.

Outputs:
- Detected intents (CURRENT_JOB, PROJECT_DETAILS, etc.)
- Extracted entities (project IDs, company IDs, technology keys)
- Tool calls to execute (graph_query_tool, portfolio_search_tool)
- Tech filters, scope, answer style preferences
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, AIMessage

from app.agent.planner.planner_llm import create_planner
from app.agent.entity_extractor import extract_entities, format_extraction_for_planner

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)

# Max dialog turns to include as context (Q+A pairs)
MAX_CONTEXT_TURNS = 2


def _extract_dialog_context(messages: list, current_question: str) -> str:
    """
    Extract recent dialog context from message history.

    Returns formatted context string with last N turns (excluding current question).
    Used to help Planner understand referential queries like "там", "этот проект".

    Args:
        messages: List of BaseMessage from state
        current_question: Current user question (to exclude from context)

    Returns:
        Formatted context string or empty string if no relevant history
    """
    if not messages or len(messages) < 2:
        return ""

    # Collect pairs of (user_question, assistant_answer)
    turns: list[tuple[str, str]] = []
    i = 0
    while i < len(messages) - 1:
        msg = messages[i]
        next_msg = messages[i + 1] if i + 1 < len(messages) else None

        if isinstance(msg, HumanMessage) and isinstance(next_msg, AIMessage):
            user_q = str(msg.content).strip()
            ai_a = str(next_msg.content).strip()

            # Skip if this is the current question
            if user_q == current_question:
                i += 2
                continue

            # Skip empty or very short responses
            if user_q and ai_a and len(ai_a) > 20:
                turns.append((user_q, ai_a))
            i += 2
        else:
            i += 1

    if not turns:
        return ""

    # Take last N turns
    recent_turns = turns[-MAX_CONTEXT_TURNS:]

    # Format as context
    context_parts = []
    for user_q, ai_a in recent_turns:
        # Truncate long answers to key info
        if len(ai_a) > 300:
            ai_a = ai_a[:300] + "..."
        context_parts.append(f"Пользователь: {user_q}\nАссистент: {ai_a}")

    return "\n\n".join(context_parts)


def planner_node(state: RAGState) -> dict:
    """
    Generate query plan using LLM.

    SYSTEMIC FIX: Uses EntityExtractor to deterministically extract
    entities BEFORE calling LLM. Planner receives EXPLICIT info about
    what entities are mentioned in question vs session context.

    Uses structured output to produce QueryPlanV3 with:
    - intents: What the user wants to know
    - entities: Extracted project/company/technology references
    - tool_calls: Which tools to call with what arguments
    - tech_filter: Technology filtering parameters
    - scope: Query scope (global/company/project)
    - render_style, answer_style: Response formatting preferences
    - confidence: Planner's confidence in the plan

    Args:
        state: Current RAGState with question and messages history

    Returns:
        Partial state update with:
        - plan: QueryPlanV3 object
        - plan_confidence: Planner's confidence (0.0-1.0)
    """
    question = state.get("question", "")
    messages = state.get("messages", [])

    # Get session context
    last_company = state.get("last_company")
    last_project = state.get("last_project")

    # SYSTEMIC FIX: Extract entities DETERMINISTICALLY before calling LLM
    # This removes the burden from LLM to parse questions and decide
    # if explicit entities override session context
    extraction = extract_entities(question)

    # Format extraction result for Planner - gives EXPLICIT info about:
    # 1. What entities are mentioned in question (ОБНАРУЖЕНО В ВОПРОСЕ)
    # 2. What session context is (КОНТЕКСТ СЕССИИ)
    # 3. Clear instruction on what to use
    entity_context = format_extraction_for_planner(
        extraction,
        last_company,
        last_project,
    )

    # Extract dialog context for multi-turn understanding
    dialog_context = _extract_dialog_context(messages, question)

    # Combine entity context with dialog context
    if dialog_context:
        full_context = f"{entity_context}\n--- Предыдущий диалог ---\n{dialog_context}"
    else:
        full_context = entity_context

    logger.info(
        "Planner: question=%r, extracted=%s, session=(company=%s, project=%s)",
        question[:50],
        [(e.type, e.value) for e in extraction.entities],
        last_company,
        last_project,
    )
    logger.debug("Planner context:\n%s", full_context[:500])

    # Get planner LLM and create planner instance
    # Lazy import to avoid circular imports
    from app.deps import planner_llm
    llm = planner_llm()
    planner = create_planner(llm)

    # Generate plan with full context (entity extraction + dialog)
    plan = planner.plan(question, context=full_context)

    logger.info(
        f"Planner result: intents={[i.value for i in plan.intents]}, "
        f"tool_calls={len(plan.tool_calls)}, confidence={plan.confidence:.2f}"
    )

    return {
        "plan": plan,
        "plan_confidence": plan.confidence,
    }
