"""
Plan Shortcuts - минимальный набор быстрых планов.

ВАЖНО: Только для абсолютно однозначных случаев!
- "контакты" -> однозначно про разработчика
- "где работает сейчас" -> однозначно про разработчика
- "кто такой Дмитрий" / "расскажи о" -> однозначно про разработчика

НЕ shortcuts: "кто ты", "что умеешь" (агент о себе, не о разработчике)

Основная оптимизация достигается через Redis cache + Prefetch (см. Фазу 2).

NOTE: Нормализация вопросов выполняется через CacheService._normalize_question(),
что убирает суффикс имени ("Дмитрия") добавляемый агентом.
"""
from __future__ import annotations

import logging
import re

from .schemas_v3 import (
    QueryPlanV3,
    IntentV3,
    ToolCallV3,
    RenderStyleV3,
    AnswerStyleV3,
    LimitsConfigV3,
)

logger = logging.getLogger(__name__)


# === ТОЛЬКО абсолютно однозначные случаи ===
# Паттерны используют fullmatch (точное совпадение) для безопасности
# NOTE: Имя владельца убирается через CacheService._normalize_question()

SAFE_SHORTCUTS: dict[str, QueryPlanV3] = {
    # Контакты разработчика (не агента!) - однозначно
    r"контакты?|связаться|как связаться|email|телефон|telegram": QueryPlanV3(
        intents=[IntentV3.CONTACTS],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "contacts"})],
        render_style=RenderStyleV3.BULLETS,
        answer_style=AnswerStyleV3.NATURAL_RU,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),
    # Текущая работа разработчика - однозначно
    r"где (сейчас )?работает|текущая работа|текущее место работы|current job": QueryPlanV3(
        intents=[IntentV3.CURRENT_JOB],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "current_job"})],
        render_style=RenderStyleV3.SHORT,
        answer_style=AnswerStyleV3.CONCISE,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),
    # Кто такой Дмитрий / расскажи о разработчике - однозначно про владельца портфолио
    # NOTE: После нормализации имя "Дмитрий/Дмитрия" убирается, поэтому паттерны без имени
    r"кто такой|кто это|кто он|о разработчике|про разработчика": QueryPlanV3(
        intents=[IntentV3.EXPERIENCE_SUMMARY],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "experience_summary"})],
        render_style=RenderStyleV3.PARAGRAPH,
        answer_style=AnswerStyleV3.NATURAL_RU,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),
}


def try_shortcut(question: str) -> QueryPlanV3 | None:
    """
    Попытка найти готовый план для однозначного вопроса.

    КОНСЕРВАТИВНЫЙ подход:
    - Только 3 абсолютно безопасных случая (контакты, работа, кто такой)
    - Используем regex fullmatch для точности
    - Всё остальное -> LLM (с последующим кэшированием в Redis)

    NOTE: Использует ту же нормализацию, что и CacheService для унификации
    cache keys и shortcuts matching.

    Args:
        question: Вопрос пользователя

    Returns:
        QueryPlanV3 если shortcut применим, иначе None (fallback to LLM + cache)
    """
    # Используем единую нормализацию из CacheService
    from ...cache.cache_service import CacheService
    normalized = CacheService._normalize_question(question)

    for pattern, plan in SAFE_SHORTCUTS.items():
        if re.fullmatch(pattern, normalized, re.IGNORECASE):
            logger.info(
                "Shortcut matched: pattern=%r, question=%r, normalized=%r",
                pattern[:30],
                question[:50],
                normalized[:50],
            )
            return plan.model_copy(deep=True)

    # Не нашли shortcut -> LLM (результат будет закэширован)
    return None
