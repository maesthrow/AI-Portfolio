"""
Plan Shortcuts - минимальный набор быстрых планов.

ВАЖНО: Только для абсолютно однозначных случаев!
- "контакты" -> однозначно про разработчика
- "где работает сейчас" -> однозначно про разработчика

НЕ shortcuts: "кто ты", "что умеешь" (агент о себе, не о разработчике)

Основная оптимизация достигается через Redis cache + Prefetch (см. Фазу 2).
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
# NOTE: Agent добавляет "Дмитрия"/"Дмитрий" к вопросам, поэтому паттерны включают опциональный суффикс

# Опциональный суффикс для имени (агент добавляет контекст)
_NAME_SUFFIX = r"( дмитрия?| dmitriy)?"

SAFE_SHORTCUTS: dict[str, QueryPlanV3] = {
    # Контакты разработчика (не агента!) - однозначно
    rf"(контакты?|связаться|как связаться|email|телефон|telegram){_NAME_SUFFIX}": QueryPlanV3(
        intents=[IntentV3.CONTACTS],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "contacts"})],
        render_style=RenderStyleV3.BULLETS,
        answer_style=AnswerStyleV3.NATURAL_RU,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),
    # Текущая работа разработчика - однозначно
    rf"(где (сейчас )?работает|текущая работа|текущее место работы|current job){_NAME_SUFFIX}": QueryPlanV3(
        intents=[IntentV3.CURRENT_JOB],
        entities=[],
        tool_calls=[ToolCallV3(tool="graph_query_tool", args={"intent": "current_job"})],
        render_style=RenderStyleV3.SHORT,
        answer_style=AnswerStyleV3.CONCISE,
        confidence=0.95,
        limits=LimitsConfigV3(),
    ),
}


def try_shortcut(question: str) -> QueryPlanV3 | None:
    """
    Попытка найти готовый план для однозначного вопроса.

    КОНСЕРВАТИВНЫЙ подход:
    - Только 2 абсолютно безопасных случая
    - Используем regex fullmatch для точности
    - Всё остальное -> LLM (с последующим кэшированием в Redis)

    Args:
        question: Вопрос пользователя

    Returns:
        QueryPlanV3 если shortcut применим, иначе None (fallback to LLM + cache)
    """
    normalized = question.lower().strip()

    # Убираем знаки препинания для более надёжного матчинга
    normalized = re.sub(r"[?!.,;:]+$", "", normalized).strip()

    for pattern, plan in SAFE_SHORTCUTS.items():
        if re.fullmatch(pattern, normalized, re.IGNORECASE):
            logger.info(
                "Shortcut matched: pattern=%r, question=%r",
                pattern[:30],
                question[:50],
            )
            return plan.model_copy(deep=True)

    # Не нашли shortcut -> LLM (результат будет закэширован в Фазе 2)
    return None
