"""
Prefetch - прогрев кэша для популярных вопросов.

Вызывается в фоне после ingest для заполнения Redis cache.
Это обеспечивает ~60-70% cache hit rate для типичных вопросов.
"""
from __future__ import annotations

import logging

from .settings import get_settings
from .cache import get_cache_service

logger = logging.getLogger(__name__)

# Популярные вопросы для прогрева кэша
# Включает ОБЕ формулировки: user-style и agent-style
#
# NOTE: LangGraph Agent переформулирует вопросы перед отправкой в RAG tool:
# - User: "расскажи об ML-проектах" → Agent: "ML-проекты Дмитрия"
# - User: "какие проекты есть" → Agent: "проекты Дмитрия"
#
# Нормализация (_normalize_question) убирает "Дмитрия", но структура разная:
# - "расскажи об ml проектах" ≠ "ml проекты"
#
# Поэтому добавляем обе формулировки для максимального cache hit rate.

POPULAR_QUESTIONS = [
    # === Проекты ===
    # User-style
    "расскажи о проектах",
    "расскажи об ML-проектах",
    "расскажи об AI-проектах",
    "какие проекты есть",
    # Agent-style (агент убирает "расскажи о/об")
    "проекты",
    "ML-проекты",
    "AI-проекты",

    # === Технологии ===
    # User-style
    "технологии",
    "какие технологии знает",
    "какими технологиями владеет",
    "стек технологий",
    # Agent-style
    "технологический стек",
    "используемые технологии",

    # === Опыт с конкретными технологиями ===
    # User-style
    "какой опыт с базами данных",
    "где применял RAG",
    # Agent-style
    "опыт работы с базами данных",
    "опыт работы с RAG",
    "опыт с PostgreSQL",
    "опыт с Python",

    # === Контакты (shortcuts, но кэшируем на всякий случай) ===
    "контакты",
    "как связаться",

    # === Опыт работы ===
    # User-style
    "опыт работы",
    "где работал",
    # Agent-style
    "опыт",
    "места работы",
    "история работы",

    # === Текущая работа (shortcut) ===
    "текущая работа",
    "где сейчас работает",

    # === Достижения ===
    # User-style
    "достижения",
    # Agent-style
    "основные достижения",
    "ключевые достижения",

    # === Навыки ===
    # User-style
    "навыки",
    # Agent-style
    "ключевые навыки",
    "профессиональные навыки",

    # === О разработчике ===
    # User-style
    "кто такой Дмитрий",
    "расскажи о Дмитрии",
    "расскажи о нем",
    # Agent-style
    "информация о Дмитрии",
    "кто он",
]


def prefetch_popular_plans() -> int:
    """
    Прогревает кэш планов для популярных вопросов.

    Вызывается после ingest для заполнения кэша.
    Вопросы из POPULAR_QUESTIONS будут закэшированы для быстрого доступа.

    Returns:
        Количество планов, загруженных через LLM (cache miss)
    """
    settings = get_settings()
    if not settings.cache_enabled:
        logger.info("Cache disabled, skipping prefetch")
        return 0

    cache = get_cache_service()
    if not cache.available:
        logger.info("Redis unavailable, skipping prefetch")
        return 0

    from .cache.plan_cache import get_plan_with_cache
    from .deps import planner_llm

    llm_calls = 0
    cached_hits = 0
    shortcut_hits = 0

    for question in POPULAR_QUESTIONS:
        try:
            _, source = get_plan_with_cache(question, planner_llm)
            if source == "llm":
                llm_calls += 1
            elif source == "cache":
                cached_hits += 1
            elif source == "shortcut":
                shortcut_hits += 1
        except Exception as e:
            logger.warning("Prefetch failed for %r: %s", question, e)

    logger.info(
        "Prefetch complete: %d questions, llm=%d, cache=%d, shortcut=%d",
        len(POPULAR_QUESTIONS),
        llm_calls,
        cached_hits,
        shortcut_hits,
    )
    return llm_calls
