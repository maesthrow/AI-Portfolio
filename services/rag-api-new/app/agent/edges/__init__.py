"""
LangGraph conditional edges (routing functions) for RAG agent.

Routing functions determine which node to execute next based on current state.

Simplified 2-LLM architecture:
1. route_scope - Routes based on scope_category (portfolio -> planner, other -> simple_llm)

Legacy routers (route_needs_search, route_answer, route_grounding) removed in 2-LLM simplification.
"""

from app.agent.edges.routing import route_scope

__all__ = [
    "route_scope",
]
