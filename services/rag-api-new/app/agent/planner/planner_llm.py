"""
Planner LLM - LLM-based query planning.

Uses structured output to generate QueryPlanV3 from user questions.
"""
from __future__ import annotations

import copy
import logging
import re
from typing import TYPE_CHECKING, Any

from langchain_core.messages import SystemMessage, HumanMessage

from .schemas import make_default_fallback_plan
from .schemas_v3 import QueryPlanV3, TechFilter, TechCategory
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

    def plan(self, question: str) -> tuple[QueryPlanV3, Any]:
        """
        Generate QueryPlanV3 from user question.

        Attempts structured output first, falls back to default plan on failure.

        Args:
            question: User's question

        Returns:
            tuple[QueryPlanV3, usage]: Plan and usage metadata (None if not available)
        """
        if not question or not question.strip():
            logger.warning("Empty question, returning default fallback plan")
            return make_default_fallback_plan(""), None

        logger.info("Planner input question=%r", truncate_text(question, limit=500))

        try:
            if self._supports_structured:
                return self._plan_structured(question)
            else:
                logger.warning("LLM doesn't support structured output, using fallback")
                return make_default_fallback_plan(question), None

        except Exception as e:
            logger.error("Planner failed: %s", e)
            return make_default_fallback_plan(question), None

    def _plan_structured(self, question: str) -> tuple[QueryPlanV3, Any]:
        """
        Use LLM's structured output capability.

        Attempts with_structured_output() with retry on failure.

        Returns:
            tuple[QueryPlanV3, usage]: Plan and accumulated usage metadata
        """
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=question),
        ]

        accumulated_usage = None  # Track usage across retries

        for attempt in range(self.max_retries + 1):
            try:
                # Select structured output method based on LLM provider:
                # GigaChat uses json_schema; DeepSeek / Qwen (ChatOpenAI) use json_mode
                _method = "json_schema" if type(self.llm).__name__ == "GigaChat" else "json_mode"
                logger.debug(
                    "Planner structured output method: %s (llm=%s)",
                    _method,
                    type(self.llm).__name__,
                )
                # include_raw=True to get both parsed result and raw AIMessage with usage_metadata
                structured_llm = self.llm.with_structured_output(
                    QueryPlanV3,
                    method=_method,
                    include_raw=True,
                )

                raw_result = structured_llm.invoke(messages)

                # Extract parsed result and raw message
                # When include_raw=True, result is {"raw": AIMessage, "parsed": QueryPlanV3, "parsing_error": ...}
                if isinstance(raw_result, dict) and "parsed" in raw_result:
                    result = raw_result.get("parsed")
                    raw_message = raw_result.get("raw")
                    # Extract usage from raw AIMessage
                    usage = self._extract_usage(raw_message)
                else:
                    # Fallback if include_raw not supported
                    result = raw_result
                    usage = self._extract_usage(result)

                if usage:
                    accumulated_usage = self._merge_usage(accumulated_usage, usage)

                if isinstance(result, QueryPlanV3):
                    # Validate the plan
                    if self._validate_plan(result):
                        sanitized = self._sanitize_plan(question, result)
                        logger.info(
                            "Plan generated: intents=%s, entities=%d, tool_calls=%d, tech_filter=%s, confidence=%.2f",
                            [i.value for i in sanitized.intents],
                            len(sanitized.entities),
                            len(sanitized.tool_calls),
                            sanitized.tech_filter.model_dump() if sanitized.tech_filter else None,
                            sanitized.confidence,
                        )
                        logger.info(
                            "Plan JSON=%s",
                            compact_json(sanitized.model_dump(mode="json")),
                        )
                        return sanitized, accumulated_usage
                    else:
                        raise ValueError("Plan validation failed")

                # If result is dict, try to parse
                if isinstance(result, dict):
                    parsed = QueryPlanV3.model_validate(result)
                    sanitized = self._sanitize_plan(question, parsed)
                    logger.info("Plan JSON=%s", compact_json(sanitized.model_dump(mode="json")))
                    return sanitized, accumulated_usage

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
        return make_default_fallback_plan(question), accumulated_usage

    def _extract_usage(self, response: Any) -> Any:
        """Extract usage_metadata from LLM response."""
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata
        if hasattr(response, "response_metadata"):
            rm = response.response_metadata or {}
            return rm.get("token_usage") or rm.get("usage")
        return None

    def _merge_usage(self, acc: Any, new: Any) -> dict:
        """Merge usage dicts (for retries)."""
        if acc is None:
            return new
        if new is None:
            return acc

        def _get(u: Any, k: str) -> int:
            if isinstance(u, dict) and k in u:
                return int(u[k] or 0)
            return int(getattr(u, k, 0) or 0)

        return {
            "prompt_tokens": _get(acc, "prompt_tokens") + _get(new, "prompt_tokens"),
            "completion_tokens": _get(acc, "completion_tokens") + _get(new, "completion_tokens"),
        }

    def _validate_plan(self, plan: QueryPlanV3) -> bool:
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

    def _sanitize_plan(self, question: str, plan: QueryPlanV3) -> QueryPlanV3:
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
            t = t.replace("„", "").replace(""", "").replace(""", "")
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

        sanitized = QueryPlanV3.model_validate(data)
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
