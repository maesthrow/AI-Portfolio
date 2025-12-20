"""
Executor module - executes QueryPlanV2 tool calls.

Orchestrates tool execution and aggregates FactsPayload.
"""
from .execute_plan import PlanExecutor

__all__ = ["PlanExecutor"]
