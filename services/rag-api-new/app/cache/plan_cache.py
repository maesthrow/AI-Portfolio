"""
Hybrid Plan Cache: shortcut -> Redis cache -> LLM fallback.

Порядок получения плана:
1. Rule-based shortcuts (мгновенно, ~0ms) - для однозначных вопросов
2. Redis cache (быстро, ~1-5ms) - для повторных запросов
3. LLM fallback (медленно, ~500-1500ms) - генерация нового плана
"""
from __future__ import annotations

import logging
from typing import Callable

from ..agent.planner.schemas_v3 import QueryPlanV3
from ..agent.planner.shortcuts import try_shortcut
from .cache_service import get_cache_service

logger = logging.getLogger(__name__)


def get_plan_with_cache(
    question: str,
    planner_llm_fn: Callable,
) -> tuple[QueryPlanV3, str]:
    """
    Получить план с использованием многоуровневого кэширования.

    Порядок:
    1. Rule-based shortcuts (мгновенно, ~0ms)
    2. Redis cache (быстро, ~1-5ms)
    3. LLM fallback (медленно, ~500-1500ms)

    Args:
        question: Вопрос пользователя
        planner_llm_fn: Функция для получения LLM (lazy initialization)

    Returns:
        tuple[QueryPlanV3, source] где source = "shortcut" | "cache" | "llm"
    """
    # 1. Try shortcut (rule-based, instant)
    plan = try_shortcut(question)
    if plan:
        logger.info(
            "Plan from shortcut: intents=%s, question=%r",
            [i.value for i in plan.intents],
            question[:50],
        )
        return plan, "shortcut"

    # 2. Try Redis cache
    cache = get_cache_service()
    cached_dict = cache.get_cached_plan(question)
    if cached_dict:
        try:
            plan = QueryPlanV3.model_validate(cached_dict)
            logger.info(
                "Plan from cache: intents=%s, question=%r",
                [i.value for i in plan.intents],
                question[:50],
            )
            return plan, "cache"
        except Exception as e:
            logger.warning("Failed to parse cached plan: %s", e)

    # 3. LLM fallback
    from ..agent.planner import PlannerLLM

    planner = PlannerLLM(planner_llm_fn())
    plan = planner.plan(question)

    # Сохраняем в кэш для следующего раза
    try:
        cache.set_cached_plan(question, plan.model_dump(mode="json"))
        logger.info(
            "Plan cached: intents=%s, question=%r",
            [i.value for i in plan.intents],
            question[:50],
        )
    except Exception as e:
        logger.warning("Failed to cache plan: %s", e)

    return plan, "llm"
