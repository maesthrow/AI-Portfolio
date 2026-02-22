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
- off_topic — запрос НЕ о портфолио разработчика: сказки, анекдоты, шутки, стихи, написание кода, погода, новости, политика, общие знания, развлечения, игры, придумывание названий, ролевые игры
- rag — вопрос о портфолио, проектах, опыте, технологиях, навыках или контактах разработчика

Если неясно — выбирай rag.
Ответь ТОЛЬКО одним словом.\
"""

_VALID_INTENTS = frozenset({
    "greeting", "thanks", "farewell", "cv_request", "off_topic", "rag",
})

CV_CONTINUATION_PROMPT = """\
Контекст: бот попросил пользователя указать email-адрес, чтобы отправить резюме.
Пользователь ответил сообщением ниже.

Определи намерение пользователя. Ответь ОДНИМ словом: YES, CANCEL или CHANGE.

YES — пользователь продолжает (пытается указать email, уточняет детали отправки, \
даже если адрес неполный или неточный):
"test@mail.ru", "на мой gmail", "на тот же адрес", "сейчас скину", \
"а можно на яндекс?", "давай на почту", "на рабочую почту", "на мой", \
"на мою почту", "скинь на email"

CANCEL — пользователь явно отказывается от отправки резюме:
"не нужно", "не хочу", "не надо", "ладно не надо", "нет спасибо", \
"отмена", "передумал", "забудь", "не нужно отправлять", "ладно, не нужно"

CHANGE — пользователь меняет тему, задаёт новый вопрос:
"расскажи о проектах", "какие технологии?", "как связаться?", \
"что ты умеешь?", "кто ты?", "контакты", "расскажи сказку"\
"""

_VALID_CV_RESULTS = frozenset({"YES", "CANCEL", "CHANGE"})


async def classify_intent(text: str, llm: BaseChatModel) -> str:
    """Classify user message intent via LLM.

    Returns one of: ``greeting``, ``thanks``, ``farewell``,
    ``cv_request``, ``off_topic``, ``rag``.

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


async def is_cv_continuation(text: str, llm: BaseChatModel) -> str:
    """Classify user message in the CV multi-turn flow.

    Used when ``pending_action == "cv_awaiting_email"`` and no email
    address was found in the message.

    Returns one of:
    - ``"yes"``    — user is still providing email / clarifying CV details
    - ``"cancel"`` — user refuses / cancels CV sending
    - ``"change"`` — user changes topic entirely

    Falls back to ``"yes"`` on error (keep user in flow rather
    than silently drop context).
    """
    try:
        response = await llm.ainvoke([
            SystemMessage(content=CV_CONTINUATION_PROMPT),
            HumanMessage(content=text),
        ])
        result = response.content.strip().upper().rstrip(".")
        if result in _VALID_CV_RESULTS:
            logger.info("LLM cv_continuation %r → %s", text[:50], result)
            return result.lower()
        logger.warning(
            "LLM cv_continuation returned invalid %r, defaulting to yes",
            result,
        )
        return "yes"
    except Exception as exc:
        logger.warning("LLM cv_continuation failed (%s), defaulting to yes", exc)
        return "yes"
