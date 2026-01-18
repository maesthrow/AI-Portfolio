"""
Critic node for RAG agent.

Evaluates retrieval results to determine if they're sufficient
to answer the user's question.

In the Quality-First architecture, critic runs ALWAYS (not conditionally)
to ensure answer quality.

Outputs:
- critic_decision: CriticDecision with sufficient/need_search flags
- needs_additional_search: Whether to run additional search
- additional_search_query: Query for additional search if needed
"""
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.critic.prompts import CRITIC_SYSTEM_PROMPT, CRITIC_USER_TEMPLATE
from app.agent.critic.schemas import CriticDecision
from app.utils.logging_utils import compact_json, truncate_text

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


def critic_node(state: RAGState) -> dict:
    """
    Evaluate retrieval results for sufficiency.

    Uses LLM to determine if the found facts are enough
    to answer the user's question properly.

    Args:
        state: Current RAGState with question, plan, merged_facts

    Returns:
        Partial state update with:
        - critic_decision: CriticDecision object
        - needs_additional_search: Boolean flag
        - additional_search_query: Query string if search needed
    """
    question = state.get("question", "")
    plan = state.get("plan")
    merged_facts = state.get("merged_facts", [])
    retrieval_found = state.get("retrieval_found", False)

    logger.info(
        f"Critic evaluating: facts={len(merged_facts)}, found={retrieval_found}"
    )

    # Build summaries for critic
    facts_preview = []
    for fact in merged_facts[:5]:
        facts_preview.append({
            "type": fact.type,
            "text": truncate_text(fact.text, limit=220),
        })

    plan_summary = "{}"
    if plan:
        plan_summary = compact_json(
            {
                "intents": [i.value for i in (plan.intents or [])],
                "entities": plan.entities,
                "tool_calls": [tc.model_dump(mode="json") for tc in (plan.tool_calls or [])],
                "confidence": plan.confidence,
            },
            limit=2400,
        )

    retrieval_summary = compact_json(
        {
            "found": retrieval_found,
            "items": len(merged_facts),
            "facts_preview": facts_preview,
        },
        limit=2400,
    )

    user_prompt = CRITIC_USER_TEMPLATE.format(
        question=truncate_text(question, limit=800),
        plan_summary=plan_summary,
        retrieval_summary=retrieval_summary,
    )

    messages = [
        SystemMessage(content=CRITIC_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        # Lazy import to avoid circular imports
        from app.deps import chat_llm
        llm = chat_llm()
        response = llm.invoke(messages)
        raw = (response.content or "").strip()

        parsed = _parse_json_object(raw)
        if not parsed:
            logger.warning(
                "Critic JSON parse failed, forcing search. raw_preview=%r",
                truncate_text(raw, limit=400),
            )
            decision = CriticDecision(
                sufficient=False,
                need_search=True,
                query=question,
                reason="critic_parse_failed",
            )
        else:
            decision = CriticDecision.model_validate(parsed)

        logger.info(
            "Critic decision: sufficient=%s need_search=%s reason=%r",
            decision.sufficient,
            decision.need_search,
            truncate_text(decision.reason, limit=200),
        )

    except Exception as e:
        logger.warning("Critic failed, forcing search: %s", e)
        decision = CriticDecision(
            sufficient=False,
            need_search=True,
            query=question,
            reason="critic_failed",
        )

    return {
        "critic_decision": decision,
        "needs_additional_search": decision.need_search,
        "additional_search_query": decision.query if decision.need_search else "",
    }


def _parse_json_object(text: str) -> dict[str, Any] | None:
    """Parse JSON object from LLM response."""
    t = (text or "").strip()
    if not t:
        return None

    try:
        return json.loads(t)
    except Exception:
        pass

    # Best-effort extraction of the first JSON object
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        return json.loads(t[start:end + 1])
    except Exception:
        return None
