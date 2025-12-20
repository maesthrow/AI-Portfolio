"""
Answer LLM - generates user-facing answers from facts.

Uses strict prompting to prevent hallucinations and ensure consistent formatting.
Based on ТЗ section 8.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage, HumanMessage

from ..planner.schemas import FactsPayload, RenderStyle, AnswerStyle
from ..render.renderer import RenderEngine, post_process_answer
from ...utils.logging_utils import truncate_text
from .prompts import (
    ANSWER_SYSTEM_PROMPT,
    ANSWER_USER_TEMPLATE,
    STYLE_INSTRUCTIONS,
    NOT_FOUND_RESPONSE,
    NOT_FOUND_BY_INTENT,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


class AnswerLLM:
    """
    Generates user-facing answer from FactsPayload.

    Uses strict prompting to prevent hallucinations and
    ensure consistent formatting.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        temperature: float = 0.3,
    ):
        """
        Initialize AnswerLLM.

        Args:
            llm: LangChain chat model
            temperature: Generation temperature (0.3 for balance)
        """
        self.llm = llm
        self.temperature = temperature
        self.renderer = RenderEngine()

    def generate(self, payload: FactsPayload) -> str:
        """
        Generate answer from FactsPayload.

        Uses deterministic rendering for structured facts,
        then LLM for natural phrasing.

        Args:
            payload: FactsPayload from Executor

        Returns:
            User-facing answer string
        """
        logger.info(
            "Answer input: found=%s items=%d sources=%d intents=%s render_style=%s answer_style=%s coverage=%.2f evidence=%r",
            payload.found,
            len(payload.items),
            len(payload.sources),
            [i.value for i in (payload.intents or [])],
            getattr(payload.render_style, "value", payload.render_style),
            getattr(payload.answer_style, "value", payload.answer_style),
            float((payload.meta or {}).get("coverage") or 0.0),
            truncate_text((payload.meta or {}).get("evidence"), limit=400),
        )

        # Handle not found case
        if not payload.found or not payload.items:
            logger.info("Answer not-found: query=%r", truncate_text(payload.query, limit=400))
            return self._get_not_found_response(payload)

        # Pre-render facts for context
        rendered_facts = self.renderer.render(
            facts=payload.items,
            style=payload.render_style,
            intents=payload.intents,
        )
        logger.info("Answer rendered_facts=%r", truncate_text(rendered_facts, limit=2000))

        # Get style instruction
        style_instruction = self._get_style_instruction(payload)

        # Format warnings
        warnings_text = ""
        if payload.warnings:
            warnings_text = f"Предупреждения: {'; '.join(payload.warnings)}"

        # Build user prompt
        user_prompt = ANSWER_USER_TEMPLATE.format(
            question=payload.query,
            facts=rendered_facts,
            style_instruction=style_instruction,
            warnings=warnings_text,
        )
        logger.info(
            "Answer prompt: system_len=%d user_len=%d user_preview=%r",
            len(ANSWER_SYSTEM_PROMPT or ""),
            len(user_prompt or ""),
            truncate_text(user_prompt, limit=2000),
        )

        # Generate answer
        messages = [
            SystemMessage(content=ANSWER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = self.llm.invoke(messages)
            answer = response.content.strip()
            logger.info("Answer raw_preview=%r", truncate_text(answer, limit=800))

            # Post-process to remove any remaining artifacts
            cleaned_answer, warnings = post_process_answer(answer)

            if warnings:
                logger.warning("Post-process removed artifacts: %s", warnings)

            logger.info("Answer final_preview=%r", truncate_text(cleaned_answer, limit=800))
            return cleaned_answer

        except Exception as e:
            logger.error("Answer generation failed: %s", e)
            # Return rendered facts as fallback
            return rendered_facts

    def _get_not_found_response(self, payload: FactsPayload) -> str:
        """Get appropriate not-found response based on intent."""
        if payload.intents:
            intent = payload.intents[0].value
            return NOT_FOUND_BY_INTENT.get(intent, NOT_FOUND_RESPONSE)
        return NOT_FOUND_RESPONSE

    def _get_style_instruction(self, payload: FactsPayload) -> str:
        """Get style instruction for the answer."""
        instructions = []

        # Add render style instruction
        render_key = payload.render_style.value
        if render_key in STYLE_INSTRUCTIONS:
            instructions.append(STYLE_INSTRUCTIONS[render_key])

        # Add answer style instruction
        answer_key = payload.answer_style.value
        if answer_key in STYLE_INSTRUCTIONS:
            instructions.append(STYLE_INSTRUCTIONS[answer_key])

        return "; ".join(instructions) if instructions else "Естественный русский язык"


def create_answer_llm(llm: BaseChatModel, temperature: float = 0.3) -> AnswerLLM:
    """
    Factory function to create AnswerLLM.

    Args:
        llm: Base LLM (will be configured with temperature)
        temperature: Answer temperature (default 0.3)

    Returns:
        Configured AnswerLLM instance
    """
    # Try to set temperature if supported
    if hasattr(llm, "temperature"):
        llm.temperature = temperature
    elif hasattr(llm, "model_kwargs"):
        llm.model_kwargs["temperature"] = temperature

    return AnswerLLM(llm=llm, temperature=temperature)
