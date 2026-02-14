"""Deterministic intent router for the top-level StateGraph.

Classifies incoming messages and routes them to the appropriate graph
node without using an LLM.  Routing decisions are regex-based and
depend on the current graph state (``pending_action``).
"""
from __future__ import annotations

import logging
import re
from typing import Any

from .graph_state import AgentState
from ..email.validation import extract_email

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CV request detection
# ---------------------------------------------------------------------------

_CV_REQUEST_PATTERNS: list[re.Pattern[str]] = [
    # "отправь / пришли / скинь / вышли / дай / получить / хочу / можно" + "резюме / cv"
    re.compile(
        r"(?:отправ|пришл|скинь|вышл|дай|получ|хоч|нужн|можн)\S*\s+(?:.*\s)?(?:резюме|cv|curriculum)",
        re.IGNORECASE,
    ),
    # "резюме / cv" + "отправ / пришл / скинь / получ"
    re.compile(
        r"(?:резюме|cv|curriculum)\s+(?:.*\s)?(?:отправ|пришл|скинь|вышл|получ)",
        re.IGNORECASE,
    ),
    # "можно / хочу / дай / дайте + резюме / cv"
    re.compile(
        r"(?:можно|хочу|нужно|дай|дайте)\s+(?:.*\s)?(?:резюме|cv)",
        re.IGNORECASE,
    ),
    # "резюме на email" (email already present in request)
    re.compile(
        r"(?:резюме|cv)\s+на\s+\S+@\S+",
        re.IGNORECASE,
    ),
]

# Patterns indicating the message is still about CV (even without email)
_CV_RELATED_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:резюме|cv|curriculum)\b", re.IGNORECASE),
    re.compile(r"\b(?:отправ|пришл|вышл|скинь)\b", re.IGNORECASE),
    re.compile(r"\b(?:почт|email|mail|@)\b", re.IGNORECASE),
    # Confirmations / clarifications within CV flow
    re.compile(r"^(?:да|нет|ладно|хорошо|ок|ok)\b", re.IGNORECASE),
]


def _is_cv_request(text: str) -> bool:
    """Return True when *text* is a request to send CV/resume."""
    return any(p.search(text) for p in _CV_REQUEST_PATTERNS)


def _is_cv_related(text: str) -> bool:
    """Return True when *text* is still related to the CV flow.

    Used to decide whether the user is continuing the CV conversation
    or has switched topics while we await their email address.
    """
    return any(p.search(text) for p in _CV_RELATED_PATTERNS)


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------


def route(state: dict[str, Any]) -> str:
    """Deterministic router for the top-level StateGraph.

    Returns one of: ``"rag"``, ``"cv_start"``, ``"cv_process"``.
    """
    messages = state.get("messages") or []
    if not messages:
        return "rag"

    last_msg = messages[-1]
    text: str = getattr(last_msg, "content", "") if hasattr(last_msg, "content") else str(last_msg)
    text = text.strip()

    pending = state.get("pending_action") or ""

    # 1. Multi-turn continuation: we asked for email and got a response
    if pending == "cv_awaiting_email":
        if extract_email(text):
            logger.info("router: cv_process (email found in pending flow)")
            return "cv_process"
        # No email — is the user still in CV context?
        if _is_cv_related(text):
            logger.info("router: cv_process (CV-related, still awaiting email)")
            return "cv_process"
        # User switched topic → reset via clear_pending → rag
        logger.info("router: rag (topic change from cv_awaiting_email)")
        return "rag"

    # 2. New CV request
    if _is_cv_request(text):
        logger.info("router: cv_start (new CV request)")
        return "cv_start"

    # 3. Everything else → existing ReAct agent
    return "rag"
