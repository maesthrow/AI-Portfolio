"""LLM-based intent classifier for the hybrid router.

Used as a fallback when regex fast-path does not match.
DeepSeek-chat with temperature=0 for deterministic classification.
"""
from __future__ import annotations

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """\
Ты — классификатор сообщений для чат-бота портфолио-сайта разработчика.

Определи категорию сообщения пользователя. Ответь ОДНИМ словом — названием категории.

Категории:
- greeting — приветствие (привет, здарова, добрый день, hi, hello, ку, йо, салют)
- thanks — благодарность (спасибо, спасиб, спс, благодарю, спасибки)
- farewell — прощание (пока, до свидания, до встречи, bye, удачи, всего доброго)
- cv_request — пользователь хочет получить или отправить резюме/CV (отправь резюме, можешь прислать cv, хочу получить резюме, скинь cv на почту)
- rag — вопрос о портфолио, проектах, опыте, технологиях, или что-либо другое

Ответь ТОЛЬКО одним словом.\
"""

_VALID_INTENTS = frozenset({"greeting", "thanks", "farewell", "cv_request", "rag"})


async def classify_intent(text: str, llm: BaseChatModel) -> str:
    """Classify user message intent via LLM.

    Returns one of: ``greeting``, ``thanks``, ``farewell``,
    ``cv_request``, ``rag``.

    Falls back to ``"rag"`` on any error (graceful degradation).
    """
    try:
        response = await llm.ainvoke([
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=text),
        ])
        result = response.content.strip().lower().rstrip(".")
        if result in _VALID_INTENTS:
            logger.info("LLM router classified %r → %s", text[:50], result)
            return result
        logger.warning("LLM router returned invalid intent %r, falling back to rag", result)
        return "rag"
    except Exception as exc:
        logger.warning("LLM router failed (%s), falling back to rag", exc)
        return "rag"
