"""CV cancel node — adaptive LLM response when user refuses CV sending.

Resets ``pending_action`` and generates a polite context-aware reply
via ``answer_llm`` (deepseek:deepseek-chat).
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)

_CV_CANCEL_SYSTEM_PROMPT = """\
Пользователь отказался от отправки резюме. Сгенерируй краткий вежливый ответ (1-2 предложения).
Подтверди отмену и предложи спросить о проектах, опыте или технологиях Дмитрия.
Не извиняйся, не используй эмодзи. Тон — дружелюбный и лаконичный.\
"""

_FALLBACK_REPLY = (
    "Хорошо, не буду отправлять. "
    "Если есть вопросы о проектах или опыте Дмитрия — спрашивайте!"
)


async def cv_cancel_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """Generate an adaptive cancellation response and reset CV flow state."""
    messages = state.get("messages") or []
    user_text = ""
    if messages:
        last_msg = messages[-1]
        user_text = (
            getattr(last_msg, "content", "")
            if hasattr(last_msg, "content")
            else str(last_msg)
        )

    try:
        from ..deps import answer_llm
        llm = answer_llm()
        response = await llm.ainvoke([
            SystemMessage(content=_CV_CANCEL_SYSTEM_PROMPT),
            HumanMessage(content=user_text),
        ])
        reply = response.content.strip()
        if not reply:
            reply = _FALLBACK_REPLY
    except Exception as exc:
        logger.warning("cv_cancel_node LLM failed (%s), using fallback", exc)
        reply = _FALLBACK_REPLY

    return {
        "messages": [AIMessage(content=reply)],
        "pending_action": "",
    }
