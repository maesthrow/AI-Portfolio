"""
Planner node for RAG agent.

Uses LLM to generate QueryPlanV3 from user question.
This is the first LLM call in the portfolio pipeline.

Outputs:
- Detected intents (CURRENT_JOB, PROJECT_DETAILS, etc.)
- Extracted entities (project IDs, company IDs, technology keys)
- Tool calls to execute (graph_query_tool, portfolio_search_tool)
- Tech filters, scope, answer style preferences
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.agent.planner.planner_llm import create_planner

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def planner_node(state: RAGState) -> dict:
    """
    Generate query plan using LLM.

    Uses structured output to produce QueryPlanV3 with:
    - intents: What the user wants to know
    - entities: Extracted project/company/technology references
    - tool_calls: Which tools to call with what arguments
    - tech_filter: Technology filtering parameters
    - scope: Query scope (global/company/project)
    - render_style, answer_style: Response formatting preferences
    - confidence: Planner's confidence in the plan

    Args:
        state: Current RAGState with question

    Returns:
        Partial state update with:
        - plan: QueryPlanV3 object
        - plan_confidence: Planner's confidence (0.0-1.0)
    """
    question = state.get("question", "")

    logger.info(f"Planner processing: {question[:100]}...")

    # Get planner LLM and create planner instance
    # Lazy import to avoid circular imports
    from app.deps import planner_llm
    llm = planner_llm()
    planner = create_planner(llm)

    # Generate plan
    plan = planner.plan(question)

    logger.info(
        f"Planner result: intents={[i.value for i in plan.intents]}, "
        f"tool_calls={len(plan.tool_calls)}, confidence={plan.confidence:.2f}"
    )

    return {
        "plan": plan,
        "plan_confidence": plan.confidence,
    }
