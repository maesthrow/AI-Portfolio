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

CV_CONTINUATION_PROMPT = """\
Контекст: бот попросил пользователя указать email-адрес, чтобы отправить резюме.
Пользователь ответил сообщением ниже.

Определи: пользователь продолжает разговор об отправке резюме \
(пытается указать email, уточняет детали отправки), \
или задаёт новый вопрос / меняет тему?

Примеры YES (продолжение — пользователь отвечает на просьбу указать email):
"test@mail.ru", "на мой gmail", "на тот же адрес", "сейчас скину", \
"а можно на яндекс?", "не хочу", "нет спасибо", "давай на почту"

Примеры NO (смена темы — пользователь задаёт новый вопрос):
"расскажи о проектах", "какие технологии?", "как связаться?", \
"как можно связаться?", "что ты умеешь?", "кто ты?", "контакты"

Ответь ОДНИМ словом: YES или NO.\
"""


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


async def is_cv_continuation(text: str, llm: BaseChatModel) -> bool:
    """Check if user message is still about the CV/email flow.

    Used when ``pending_action == "cv_awaiting_email"`` and regex
    didn't match.  Returns ``True`` to stay in CV flow,
    ``False`` to treat as topic change.

    Falls back to ``True`` on error (keep user in flow rather
    than silently drop context).
    """
    try:
        response = await llm.ainvoke([
            SystemMessage(content=CV_CONTINUATION_PROMPT),
            HumanMessage(content=text),
        ])
        result = response.content.strip().upper().rstrip(".")
        is_cv = result == "YES"
        logger.info("LLM cv_continuation %r → %s", text[:50], result)
        return is_cv
    except Exception as exc:
        logger.warning("LLM cv_continuation failed (%s), defaulting to True", exc)
        return True
