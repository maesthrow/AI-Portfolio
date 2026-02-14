"""Deterministic smalltalk node for greetings, thanks and farewells.

No LLM calls — returns canned responses instantly.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

from .router import _classify_smalltalk

_RESPONSES: dict[str, str] = {
    "greeting": (
        "Привет! Я — AI-ассистент портфолио Дмитрия. "
        "Спросите меня о проектах, технологиях или опыте работы."
    ),
    "thanks": "Рад помочь! Если будут ещё вопросы — обращайтесь.",
    "farewell": "До свидания! Буду рад помочь, если появятся вопросы.",
}

_DEFAULT = "Чем могу помочь? Спросите о проектах, опыте или технологиях Дмитрия."


def smalltalk_node(state: dict[str, Any]) -> dict:
    """Return a canned response based on smalltalk category."""
    messages = state.get("messages") or []
    text = ""
    if messages:
        last = messages[-1]
        text = getattr(last, "content", "") if hasattr(last, "content") else str(last)
        text = text.strip()

    category = _classify_smalltalk(text)
    reply = _RESPONSES.get(category or "", _DEFAULT)

    return {"messages": [AIMessage(content=reply)]}
