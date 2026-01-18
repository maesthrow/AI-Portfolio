"""
LangGraph conditional edges (routing functions) for RAG agent.

Routing functions determine which node to execute next based on current state.

Available routers:
1. route_scope - Routes based on scope_category (portfolio/small_talk/off_topic/harmful)
2. route_needs_search - Routes based on critic's additional search decision
3. route_answer - Routes to deterministic or LLM answer generation
4. route_grounding - Routes based on grounding verification result
"""

from app.agent.edges.routing import (
    route_scope,
    route_needs_search,
    route_answer,
    route_grounding,
)

__all__ = [
    "route_scope",
    "route_needs_search",
    "route_answer",
    "route_grounding",
]
