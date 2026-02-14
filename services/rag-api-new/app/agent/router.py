"""Hybrid intent router for the top-level StateGraph.

Architecture:
1. ``pending_action`` check — deterministic, state-based (CV multi-turn)
2. Regex fast-path — covers ~70% of messages (greetings, thanks, obvious CV)
3. LLM fallback — DeepSeek-chat classifies ambiguous messages (~300ms)

The router is a **graph node** (not a conditional edge function) so it
can run async LLM calls and write ``_route_intent`` into state.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from langchain_core.runnables import RunnableConfig

from ..email.validation import extract_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex fast-path patterns
# ---------------------------------------------------------------------------

_GREETING_RE: list[re.Pattern[str]] = [
    re.compile(
        r"^(?:привет\w*|здравствуй\w*|здорово|здаров\w*|хай|хей|hello|hi|hey|ку|йо|салют)\s*[!.?]*$",
        re.IGNORECASE,
    ),
    re.compile(r"^добр(?:ый|ое|ого)\s+(?:день|утро|вечер|времени)\s*[!.]*$", re.IGNORECASE),
]

_THANKS_RE: list[re.Pattern[str]] = [
    re.compile(
        r"^(?:спасибо|спасиб|спс|благодарю|благодарствую|спасибки|thanks?|thank\s+you)\s*[!.]*$",
        re.IGNORECASE,
    ),
]

_FAREWELL_RE: list[re.Pattern[str]] = [
    re.compile(
        r"^(?:пока|до свидания|до встречи|прощай|всего доброго|удачи|bye|goodbye)\s*[!.]*$",
        re.IGNORECASE,
    ),
]

_CV_REQUEST_RE: list[re.Pattern[str]] = [
    # verb + резюме/cv
    re.compile(
        r"(?:отправ|пришл|присл|скинь|вышл|дай|получ|хоч|нужн|мож)\S*\s+(?:.*\s)?(?:резюме|cv|curriculum)",
        re.IGNORECASE,
    ),
    # резюме/cv + verb
    re.compile(
        r"(?:резюме|cv|curriculum)\s+(?:.*\s)?(?:отправ|пришл|присл|скинь|вышл|получ)",
        re.IGNORECASE,
    ),
    # резюме на email@
    re.compile(r"(?:резюме|cv)\s+на\s+\S+@\S+", re.IGNORECASE),
]

# Patterns for CV multi-turn continuation (is user still talking about CV?)
_CV_RELATED_RE: list[re.Pattern[str]] = [
    re.compile(r"\b(?:резюме|cv|curriculum)\b", re.IGNORECASE),
    re.compile(r"\b(?:отправ|пришл|присл|вышл|скинь)\b", re.IGNORECASE),
    re.compile(r"\b(?:почт|email|mail|@)\b", re.IGNORECASE),
    re.compile(r"^(?:да|нет|ладно|хорошо|ок|ok)\b", re.IGNORECASE),
]


def _regex_classify(text: str) -> str | None:
    """Try to classify via regex. Returns intent or ``None``."""
    # Smalltalk only for short standalone messages
    if len(text) <= 60:
        if any(p.search(text) for p in _THANKS_RE):
            return "thanks"
        if any(p.search(text) for p in _FAREWELL_RE):
            return "farewell"
        if any(p.search(text) for p in _GREETING_RE):
            return "greeting"

    if any(p.search(text) for p in _CV_REQUEST_RE):
        return "cv_request"

    return None


def _is_cv_related(text: str) -> bool:
    """Check if text is still about the CV flow (for multi-turn)."""
    return any(p.search(text) for p in _CV_RELATED_RE)


# ---------------------------------------------------------------------------
# Intent → graph route mapping
# ---------------------------------------------------------------------------

_INTENT_TO_ROUTE: dict[str, str] = {
    "greeting": "greeting",
    "thanks": "thanks",
    "farewell": "farewell",
    "cv_request": "cv_start",
    "rag": "rag",
}


# ---------------------------------------------------------------------------
# Router node
# ---------------------------------------------------------------------------


async def router_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """Hybrid router: regex fast-path → LLM fallback.

    Writes ``_route_intent`` into state for downstream nodes
    (e.g. ``smalltalk_node`` reads it to pick the right response).
    """
    messages = state.get("messages") or []
    if not messages:
        return {"_route_intent": "rag"}

    last_msg = messages[-1]
    text: str = (
        getattr(last_msg, "content", "")
        if hasattr(last_msg, "content")
        else str(last_msg)
    )
    text = text.strip()

    pending = state.get("pending_action") or ""

    # 1. Multi-turn CV continuation (deterministic, state-based)
    if pending == "cv_awaiting_email":
        if extract_email(text):
            logger.info("router: cv_process (email found in pending flow)")
            return {"_route_intent": "cv_process"}
        if _is_cv_related(text):
            logger.info("router: cv_process (CV-related, still awaiting email)")
            return {"_route_intent": "cv_process"}
        logger.info("router: rag (topic change from cv_awaiting_email)")
        return {"_route_intent": "rag"}

    # 2. Regex fast-path
    intent = _regex_classify(text)
    if intent:
        route = _INTENT_TO_ROUTE.get(intent, "rag")
        logger.info("router: %s (regex → %s)", route, intent)
        return {"_route_intent": route}

    # 3. LLM fallback
    from .router_llm import classify_intent
    from ..deps import router_llm

    llm_intent = await classify_intent(text, router_llm())
    route = _INTENT_TO_ROUTE.get(llm_intent, "rag")
    logger.info("router: %s (LLM → %s)", route, llm_intent)
    return {"_route_intent": route}


def route_edge(state: dict[str, Any]) -> str:
    """Read ``_route_intent`` from state for conditional edge."""
    return state.get("_route_intent") or "rag"
