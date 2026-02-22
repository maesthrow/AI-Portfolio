"""Deterministic off-topic refusal node.

Returns a polite refusal with suggested on-topic questions.
No LLM calls — instant response, same pattern as ``smalltalk_node``.
"""
from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage

_REFUSAL = (
    "Я — AI-ассистент портфолио Дмитрия и отвечаю только на вопросы "
    "о его проектах, опыте и навыках.\n\n"
    "Попробуйте спросить:\n"
    "• Какие проекты есть в портфолио?\n"
    "• Где применял RAG?\n"
    "• Какие технологии знает Дмитрий?"
)


def offtopic_node(state: dict[str, Any]) -> dict:
    """Return a polite off-topic refusal with suggested questions."""
    return {"messages": [AIMessage(content=_REFUSAL)]}
