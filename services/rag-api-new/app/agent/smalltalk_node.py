"""Deterministic smalltalk node for greetings, thanks and farewells.

No LLM calls — returns canned responses instantly.
Reads ``_route_intent`` from state (set by ``router_node``).
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

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
    """Return a canned response based on ``_route_intent``."""
    intent = state.get("_route_intent") or ""
    reply = _RESPONSES.get(intent, _DEFAULT)
    return {"messages": [AIMessage(content=reply)]}
