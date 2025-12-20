"""
Planner LLM - LLM-based query planning.

Uses structured output to generate QueryPlanV2 from user questions.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage, HumanMessage

from .schemas import QueryPlanV2, make_default_fallback_plan
from .prompts import PLANNER_SYSTEM_PROMPT, PLANNER_REPAIR_PROMPT
from ...rag.entities import get_entity_registry
from ...rag.search_types import EntityType
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
                        sanitized = self._sanitize_plan(question, result)
                        logger.info(
                            "Plan generated: intents=%s, entities=%d, tool_calls=%d, confidence=%.2f",
                            [i.value for i in sanitized.intents],
                            len(sanitized.entities),
                            len(sanitized.tool_calls),
                            sanitized.confidence,
                        )
                        logger.info(
                            "Plan JSON=%s",
                            compact_json(sanitized.model_dump(mode="json")),
                        )
                        return sanitized
                    else:
                        raise ValueError("Plan validation failed")

                # If result is dict, try to parse
                if isinstance(result, dict):
                    parsed = QueryPlanV2.model_validate(result)
                    sanitized = self._sanitize_plan(question, parsed)
                    logger.info("Plan JSON=%s", compact_json(sanitized.model_dump(mode="json")))
                    return sanitized

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

    def _sanitize_plan(self, question: str, plan: QueryPlanV2) -> QueryPlanV2:
        """
        Best-effort post-processing of an LLM-generated plan.

        Fixes common failure modes observed in logs:
        - invalid entity IDs (wrong slug / wrong type)
        - mismatched intent vs entity type (e.g. project_details + company)
        - "what did he do at company X?" questions routed to project_details
        """
        registry = get_entity_registry()
        original = plan.model_dump(mode="json")
        data = copy.deepcopy(original)

        def _norm_key(text: str | None) -> str:
            if not text:
                return ""
            t = text.strip().lower()
            t = t.replace("«", "").replace("»", "")
            t = t.replace("„", "").replace("“", "").replace("”", "")
            t = re.sub(r"\s+", " ", t)
            return t

        type_map = {
            "project": EntityType.PROJECT,
            "company": EntityType.COMPANY,
            "technology": EntityType.TECHNOLOGY,
            "person": EntityType.PERSON,
        }

        def _id_from_entity(entity_type: EntityType, slug: str) -> str:
            return f"{entity_type.value}:{slug}"

        def _resolve_canonical_id(canonical_id: str | None) -> tuple[EntityType, str, str] | None:
            if not canonical_id or ":" not in canonical_id:
                return None
            raw_type, raw_slug = canonical_id.split(":", 1)
            entity_type = type_map.get(_norm_key(raw_type))
            if not entity_type:
                return None
            slug = (raw_slug or "").strip()
            found = registry.find_entity(slug) or registry.find_entity(_norm_key(slug))
            if found and found.type == entity_type:
                return found.type, found.slug, found.name
            # Fallback: keep slug even if not registered (still useful for vector search)
            return entity_type, slug, slug

        def _resolve_entity(entity: dict) -> dict:
            raw_id = entity.get("id")
            raw_name = entity.get("name")

            candidates: list[str] = []
            for v in (raw_id, raw_name):
                if isinstance(v, str) and v.strip():
                    candidates.append(v)
            if isinstance(raw_id, str) and ":" in raw_id:
                candidates.append(raw_id.split(":", 1)[1])

            resolved: tuple[EntityType, str, str] | None = None
            for c in candidates:
                key = _norm_key(c)
                found = registry.find_entity(c) or registry.find_entity(key)
                if found:
                    resolved = (found.type, found.slug, found.name)
                    break
                extracted = registry.extract_entities(c)
                if extracted:
                    found = extracted[0]
                    resolved = (found.type, found.slug, found.name)
                    break

            if not resolved:
                return entity

            etype, slug, name = resolved
            return {
                **entity,
                "type": etype.value,
                "id": _id_from_entity(etype, slug),
                "name": name,
            }

        # Normalize entities
        data["entities"] = [_resolve_entity(e) for e in data.get("entities", [])]

        # Normalize tool_call entity_id
        for tc in data.get("tool_calls", []):
            args = tc.get("args") or {}
            if not isinstance(args, dict):
                continue
            entity_id = args.get("entity_id")
            if isinstance(entity_id, str) and entity_id.strip():
                entity_stub = {"type": "", "id": entity_id, "name": ""}
                normalized = _resolve_entity(entity_stub).get("id")
                if normalized:
                    args["entity_id"] = normalized
                tc["args"] = args

        sanitized = QueryPlanV2.model_validate(data)
        if sanitized.model_dump(mode="json") != original:
            logger.info("Plan sanitized JSON=%s", compact_json(sanitized.model_dump(mode="json")))
        return sanitized


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
