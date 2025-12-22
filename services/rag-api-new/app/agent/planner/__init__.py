"""
Planner module - LLM-based query planning.

Analyzes user questions and produces structured QueryPlanV2
with intents, entities, and tool calls.
"""
from .schemas import (
    IntentV2,
    RenderStyle,
    AnswerStyle,
    EntityV2,
    ToolCall,
    FallbackConfig,
    LimitsConfig,
    QueryPlanV2,
    FactItem,
    FactsPayload,
)

# Lazy import for PlannerLLM to avoid loading langchain_core at import time
# This allows tests to run without langchain_core installed
_PlannerLLM = None


def __getattr__(name: str):
    """Lazy import for PlannerLLM."""
    global _PlannerLLM
    if name == "PlannerLLM":
        if _PlannerLLM is None:
            from .planner_llm import PlannerLLM as _PlannerLLM_impl
            _PlannerLLM = _PlannerLLM_impl
        return _PlannerLLM
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "IntentV2",
    "RenderStyle",
    "AnswerStyle",
    "EntityV2",
    "ToolCall",
    "FallbackConfig",
    "LimitsConfig",
    "QueryPlanV2",
    "FactItem",
    "FactsPayload",
    "PlannerLLM",
]
