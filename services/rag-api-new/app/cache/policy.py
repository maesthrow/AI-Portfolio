"""
Cache Policy - логика определения кэшируемости ответов.

Определяет, какие ответы стоит кэшировать на основе:
- Типа intent (фактические vs. динамические)
- Confidence уровня
- Результата grounding проверки
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agent.planner.schemas import FactsPayload
    from ..agent.planner.schemas_v3 import QueryPlanV3, GroundingResult

logger = logging.getLogger(__name__)


# Интенты, ответы на которые имеет смысл кэшировать.
# Это фактические вопросы с детерминированными ответами.
CACHEABLE_INTENTS = frozenset({
    # Контактная информация - статичная
    "contacts",

    # Текущая работа - относительно статичная
    "current_job",

    # Технологии - статичные данные
    "technology_overview",
    "technology_usage",

    # Детали проектов - статичные
    "project_details",
    "project_achievements",
    "project_tech_stack",

    # Опыт работы - статичный
    "experience_summary",
})


# Интенты, которые НЕ стоит кэшировать
NON_CACHEABLE_INTENTS = frozenset({
    # Общие вопросы - слишком вариативны
    "general_unstructured",
})


def should_cache(
    facts_payload: FactsPayload,
    grounding_result: GroundingResult,
    plan: QueryPlanV3,
    min_confidence: float = 0.7,
    answer: str = "",
    min_answer_length: int = 100,
) -> bool:
    """
    Определить, нужно ли кэшировать ответ.

    Критерии кэширования:
    1. Найдены данные (facts_payload.found = True)
    2. Достаточная уверенность (confidence >= min_confidence)
    3. Ответ прошёл grounding (grounded = True, action = "accept")
    4. Intent входит в список кэшируемых
    5. Ответ достаточно длинный (не шаблонный/детерминистический)

    Args:
        facts_payload: Результат выполнения плана
        grounding_result: Результат проверки на галлюцинации
        plan: Исполненный план запроса
        min_confidence: Минимальный порог уверенности
        answer: Сгенерированный ответ
        min_answer_length: Минимальная длина ответа для кэширования

    Returns:
        True если ответ стоит кэшировать
    """
    # 1. Проверяем что данные найдены
    if not facts_payload.found:
        logger.debug("Cache policy: NOT cacheable - no data found")
        return False

    # 2. Проверяем длину ответа (фильтрует шаблонные/детерминистические ответы)
    if answer and len(answer) < min_answer_length:
        logger.debug(
            "Cache policy: NOT cacheable - answer too short (%d < %d chars)",
            len(answer),
            min_answer_length,
        )
        return False

    # 3. Проверяем confidence
    confidence = facts_payload.meta.get("coverage", 0.0)
    if confidence < min_confidence:
        logger.debug(
            "Cache policy: NOT cacheable - low confidence %.2f < %.2f",
            confidence,
            min_confidence,
        )
        return False

    # 4. Проверяем grounding
    if not grounding_result.grounded:
        logger.debug("Cache policy: NOT cacheable - not grounded")
        return False

    if grounding_result.action != "accept":
        logger.debug(
            "Cache policy: NOT cacheable - grounding action=%s",
            grounding_result.action,
        )
        return False

    # 5. Проверяем intent
    intents = plan.intents or []
    intent_values = {i.value if hasattr(i, 'value') else str(i) for i in intents}

    # Проверяем что хотя бы один intent кэшируемый
    has_cacheable_intent = bool(intent_values & CACHEABLE_INTENTS)

    if not has_cacheable_intent:
        logger.debug(
            "Cache policy: NOT cacheable - no cacheable intent in %s",
            intent_values,
        )
        return False

    # Проверяем что нет non-cacheable интентов
    has_non_cacheable = bool(intent_values & NON_CACHEABLE_INTENTS)
    if has_non_cacheable:
        logger.debug(
            "Cache policy: NOT cacheable - has non-cacheable intent in %s",
            intent_values,
        )
        return False

    logger.info(
        "Cache policy: CACHEABLE - intents=%s, confidence=%.2f, grounded=%s, answer_len=%d",
        intent_values,
        confidence,
        grounding_result.grounded,
        len(answer) if answer else 0,
    )

    return True


def get_cache_key_components(question: str, plan: QueryPlanV3) -> dict:
    """
    Получить компоненты для формирования ключа кэша.

    Может использоваться для более гранулярного кэширования
    (например, с учётом entities).

    Args:
        question: Вопрос пользователя
        plan: План запроса

    Returns:
        Словарь с компонентами ключа
    """
    intents = plan.intents or []
    intent_values = sorted(i.value if hasattr(i, 'value') else str(i) for i in intents)

    components = {
        "question": question.lower().strip(),
        "intents": intent_values,
    }

    # Добавляем scope если есть
    if plan.scope:
        if plan.scope.project_id:
            components["project_id"] = plan.scope.project_id
        if plan.scope.company_id:
            components["company_id"] = plan.scope.company_id

    # Добавляем tech_filter если есть
    if plan.tech_filter and plan.tech_filter.category:
        components["tech_category"] = plan.tech_filter.category.value

    return components
