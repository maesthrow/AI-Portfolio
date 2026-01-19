"""
Output formatter node for RAG agent.

Formats the final response with:
- answer: The generated answer text
- sources: List of source references
- found: Whether information was found
- intents: Detected intents
- confidence: Overall confidence
- grounded: Whether answer is grounded

This is a deterministic node (no LLM call).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import AIMessage

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def output_formatter_node(state: RAGState) -> dict:
    """
    Format final response for API output.

    Collects all relevant state fields and builds
    a structured response dict.

    Args:
        state: Current RAGState with answer, sources, grounding_result, etc.

    Returns:
        Partial state update with:
        - final_response: Complete response dict for API
    """
    answer = state.get("answer", "")
    sources = state.get("sources", [])
    plan = state.get("plan")
    grounding_result = state.get("grounding_result")
    retrieval_found = state.get("retrieval_found", False)
    normalized_facts = state.get("normalized_facts", [])
    scope_category = state.get("scope_category", "portfolio")

    # Determine intents
    intents = []
    if plan and plan.intents:
        intents = [i.value for i in plan.intents]

    # Calculate overall confidence
    confidence = 0.0
    if plan:
        confidence = plan.confidence
    if grounding_result:
        confidence = min(confidence, grounding_result.confidence) if confidence else grounding_result.confidence

    # Determine if grounded
    grounded = True
    if grounding_result:
        grounded = grounding_result.grounded

    # Format sources for output
    # Sources can be dicts (from new tool_executor) or SourceInfo objects (legacy)
    formatted_sources = []
    for source in sources:
        if isinstance(source, dict):
            # New format: sources are dicts from tool_executor
            formatted_sources.append({
                "id": source.get("id", ""),
                "label": source.get("label") or source.get("title") or source.get("name", ""),
                "type": source.get("type", ""),
            })
        else:
            # Legacy format: SourceInfo objects
            formatted_sources.append({
                "id": source.id,
                "label": source.label,
                "type": source.type,
            })

    # Build final response
    final_response: dict[str, Any] = {
        "answer": answer,
        "sources": formatted_sources,
        "found": retrieval_found or bool(normalized_facts),
        "intents": intents,
        "confidence": confidence,
        "grounded": grounded,
        "scope_category": scope_category,
    }

    # Add optional fields
    if grounding_result and grounding_result.ungrounded_entities:
        final_response["ungrounded_entities"] = grounding_result.ungrounded_entities

    if plan:
        final_response["render_style"] = plan.render_style.value if plan.render_style else "bullets"
        final_response["answer_style"] = plan.answer_style.value if plan.answer_style else "natural_ru"

    logger.info(
        f"Output: answer_len={len(answer)}, sources={len(formatted_sources)}, "
        f"found={final_response['found']}, grounded={grounded}, "
        f"confidence={confidence:.2f}"
    )

    # Add AIMessage to messages for session memory (dialog context)
    # This enables multi-turn conversations where Planner can see previous Q&A
    ai_message = AIMessage(content=answer)

    return {
        "final_response": final_response,
        "messages": [ai_message],  # Merged via add_messages annotation
    }
