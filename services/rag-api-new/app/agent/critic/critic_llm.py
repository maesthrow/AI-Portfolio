from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from langchain_core.messages import SystemMessage, HumanMessage

from .prompts import CRITIC_SYSTEM_PROMPT, CRITIC_USER_TEMPLATE
from .schemas import CriticDecision
from ..planner.schemas import FactsPayload, QueryPlanV2
from ...utils.logging_utils import compact_json, truncate_text

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)


def _parse_json_object(text: str) -> dict[str, Any] | None:
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
        return json.loads(t[start : end + 1])
    except Exception:
        return None


class CriticLLM:
    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def evaluate(self, question: str, plan: QueryPlanV2, payload: FactsPayload) -> CriticDecision:
        facts_preview = []
        for item in (payload.items or [])[:5]:
            facts_preview.append(
                {
                    "type": item.type,
                    "text": truncate_text(item.text, limit=220),
                }
            )

        evidence = (payload.meta or {}).get("evidence")
        evidence_preview = truncate_text(str(evidence or ""), limit=400)

        plan_summary = compact_json(
            {
                "intents": [i.value for i in (plan.intents or [])],
                "entities": [e.model_dump(mode="json") for e in (plan.entities or [])],
                "tool_calls": [tc.model_dump(mode="json") for tc in (plan.tool_calls or [])],
                "fallback": plan.fallback.model_dump(mode="json") if plan.fallback else None,
                "limits": plan.limits.model_dump(mode="json") if plan.limits else None,
                "render_style": getattr(plan.render_style, "value", plan.render_style),
                "answer_style": getattr(plan.answer_style, "value", plan.answer_style),
                "confidence": plan.confidence,
            },
            limit=2400,
        )

        retrieval_summary = compact_json(
            {
                "found": payload.found,
                "items": len(payload.items or []),
                "sources": len(payload.sources or []),
                "facts_preview": facts_preview,
                "evidence_preview": evidence_preview,
                "coverage": float((payload.meta or {}).get("coverage") or 0.0),
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
            resp = self.llm.invoke(messages)
            raw = (resp.content or "").strip()
            parsed = _parse_json_object(raw)
            if not parsed:
                logger.warning("Critic JSON parse failed, forcing search. raw_preview=%r", truncate_text(raw, limit=400))
                return CriticDecision(sufficient=False, need_search=True, query=question, reason="critic_parse_failed")
            decision = CriticDecision.model_validate(parsed)
            logger.info(
                "Critic decision: sufficient=%s need_search=%s reason=%r query=%r",
                decision.sufficient,
                decision.need_search,
                truncate_text(decision.reason, limit=200),
                truncate_text(decision.query, limit=200),
            )
            return decision
        except Exception as e:
            logger.warning("Critic failed, forcing search: %s", e)
            return CriticDecision(sufficient=False, need_search=True, query=question, reason="critic_failed")

