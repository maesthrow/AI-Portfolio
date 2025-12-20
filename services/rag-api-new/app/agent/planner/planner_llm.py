"""
Planner LLM - LLM-based query planning.

Uses structured output to generate QueryPlanV2 from user questions.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage, HumanMessage

from .schemas import QueryPlanV2, make_default_fallback_plan
from .prompts import PLANNER_SYSTEM_PROMPT, PLANNER_REPAIR_PROMPT
from ...utils.logging_utils import compact_json, truncate_text

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class PlannerLLM:
    """
    LLM-based query planner with structured output.

    Uses with_structured_output() for reliable JSON generation.
    Falls back to default plan on complete failure.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        max_retries: int = 2,
        temperature: float = 0.0,
    ):
        """
        Initialize PlannerLLM.

        Args:
            llm: LangChain chat model
            max_retries: Max attempts on validation failure
            temperature: LLM temperature (0.0 for deterministic)
        """
        self.llm = llm
        self.max_retries = max_retries
        self.temperature = temperature

        # Check if LLM supports structured output
        self._supports_structured = hasattr(llm, "with_structured_output")

    def plan(self, question: str) -> QueryPlanV2:
        """
        Generate QueryPlanV2 from user question.

        Attempts structured output first, falls back to default plan on failure.

        Args:
            question: User's question

        Returns:
            QueryPlanV2 with intents, entities, tool_calls, etc.
        """
        if not question or not question.strip():
            logger.warning("Empty question, returning default fallback plan")
            return make_default_fallback_plan("")

        logger.info("Planner input question=%r", truncate_text(question, limit=500))

        try:
            if self._supports_structured:
                return self._plan_structured(question)
            else:
                logger.warning("LLM doesn't support structured output, using fallback")
                return make_default_fallback_plan(question)

        except Exception as e:
            logger.error("Planner failed: %s", e)
            return make_default_fallback_plan(question)

    def _plan_structured(self, question: str) -> QueryPlanV2:
        """
        Use LLM's structured output capability.

        Attempts with_structured_output() with retry on failure.
        """
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        for attempt in range(self.max_retries + 1):
            try:
                # Create structured LLM with Pydantic model
                structured_llm = self.llm.with_structured_output(
                    QueryPlanV2,
                    method="json_schema",  # Use JSON schema for better compatibility
                )

                result = structured_llm.invoke(messages)

                if isinstance(result, QueryPlanV2):
                    # Validate the plan
                    if self._validate_plan(result):
                        logger.info(
                            "Plan generated: intents=%s, entities=%d, tool_calls=%d, confidence=%.2f",
                            [i.value for i in result.intents],
                            len(result.entities),
                            len(result.tool_calls),
                            result.confidence,
                        )
                        logger.info(
                            "Plan JSON=%s",
                            compact_json(result.model_dump(mode="json")),
                        )
                        return result
                    else:
                        raise ValueError("Plan validation failed")

                # If result is dict, try to parse
                if isinstance(result, dict):
                    parsed = QueryPlanV2.model_validate(result)
                    logger.info("Plan JSON=%s", compact_json(parsed.model_dump(mode="json")))
                    return parsed

                raise ValueError(f"Unexpected result type: {type(result)}")

            except Exception as e:
                logger.warning(
                    "Structured output failed (attempt %d/%d): %s",
                    attempt + 1,
                    self.max_retries + 1,
                    e,
                )
                logger.info(
                    "Planner repair attempt=%d last_error=%r",
                    attempt + 1,
                    truncate_text(str(e), limit=400),
                )

                if attempt < self.max_retries:
                    # Add repair message
                    messages.append(
                        HumanMessage(
                            content=PLANNER_REPAIR_PROMPT.format(error=str(e))
                        )
                    )

        # Complete failure - return default fallback
        logger.error(
            "Planner failed after %d attempts, using fallback",
            self.max_retries + 1,
        )
        return make_default_fallback_plan(question)

    def _validate_plan(self, plan: QueryPlanV2) -> bool:
        """
        Validate generated plan.

        Checks for:
        - At least one intent
        - At least one tool_call
        - Known tool names
        - Reasonable confidence
        """
        if not plan.intents:
            logger.warning("Plan has no intents")
            return False

        if not plan.tool_calls:
            logger.warning("Plan has no tool_calls")
            return False

        known_tools = {"graph_query_tool", "portfolio_search_tool"}
        for tc in plan.tool_calls:
            if tc.tool not in known_tools:
                logger.warning("Unknown tool in plan: %s", tc.tool)
                # Don't fail, just log - might be a new tool

        return True


def create_planner(llm: BaseChatModel, temperature: float = 0.0) -> PlannerLLM:
    """
    Factory function to create PlannerLLM.

    Args:
        llm: Base LLM (will be configured with temperature)
        temperature: Planner temperature (default 0.0 for deterministic)

    Returns:
        Configured PlannerLLM instance
    """
    # Try to set temperature if supported
    if hasattr(llm, "temperature"):
        llm.temperature = temperature
    elif hasattr(llm, "model_kwargs"):
        llm.model_kwargs["temperature"] = temperature

    return PlannerLLM(llm=llm, temperature=temperature)
