"""
Agent Tools v2 - новые инструменты для Graph-RAG.

Включает graph_query_tool для структурированных запросов к графу знаний.
"""
from __future__ import annotations

import logging
from langchain.tools import tool

from ..deps import settings
from ..graph.query import graph_query
from ..rag.search_types import Intent

logger = logging.getLogger(__name__)


@tool("graph_query_tool")
def graph_query_tool(intent: str, entity_key: str = "") -> dict:
    """
    Запрос к графу знаний портфолио для получения структурированных фактов.

    Используй для быстрого получения конкретной информации:
    - achievements: список достижений (опционально по проекту/компании)
    - current_job: текущее место работы
    - contacts: контактная информация
    - languages: языки программирования
    - technologies: технологии (опционально по проекту)
    - project_details: детали проекта (требует entity_key)
    - experience: опыт работы

    Args:
        intent: Тип запроса (achievements, current_job, contacts, languages,
                technologies, project_details, experience)
        entity_key: Опциональный slug проекта/компании для фильтрации

    Returns:
        Словарь с полями:
        - items: список структурированных фактов
        - found: True если найдены данные
        - sources: источники информации
        - confidence: уверенность (0.0-1.0)
    """
    cfg = settings()

    # Проверка feature flag
    if not cfg.agent_fact_tool:
        logger.warning("graph_query_tool called but agent_fact_tool is disabled")
        return {
            "items": [],
            "found": False,
            "message": "Graph query tool is disabled",
        }

    # Парсинг intent
    try:
        intent_enum = Intent(intent.lower())
    except ValueError:
        valid_intents = [i.value for i in Intent if i != Intent.GENERAL]
        return {
            "items": [],
            "found": False,
            "message": f"Unknown intent: {intent}. Use one of: {valid_intents}",
        }

    logger.info("graph_query_tool: intent=%r, entity_key=%r", intent, entity_key)

    # Выполнение запроса
    result = graph_query(intent_enum, entity_key or None)

    return {
        "items": result.items,
        "found": result.found,
        "sources": result.sources,
        "confidence": result.confidence,
    }


@tool("portfolio_rag_tool_v2")
def portfolio_rag_tool_v2(question: str) -> dict:
    """
    Улучшенный RAG-инструмент с планированием запросов.

    Автоматически определяет намерение, извлекает сущности,
    и выбирает оптимальную стратегию поиска (граф или гибридный).

    Используй для любых вопросов о портфолио:
    - проекты, компании, технологии
    - опыт работы, достижения
    - контакты, навыки

    Args:
        question: Вопрос о портфолио на русском или английском

    Returns:
        Словарь с полями:
        - answer: текстовый ответ (если гибридный поиск)
        - items: структурированные факты (если граф)
        - sources: источники информации
        - confidence: уверенность
        - intent: определённое намерение
        - used_graph: использовался ли граф
    """
    cfg = settings()

    # Проверка feature flag
    if not cfg.rag_router_v2:
        # Fallback на старый инструмент
        from .tools import portfolio_rag_tool
        return portfolio_rag_tool.invoke(question)

    logger.info("portfolio_rag_tool_v2: question=%r", question[:100])

    from ..rag.search import portfolio_search
    result = portfolio_search(question=question)

    # === Epic 3: FormatRenderer integration ===
    if cfg.format_v2_enabled:
        from ..rag.formatter import FormatRenderer, format_not_found_response

        renderer = FormatRenderer()

        if not result.found:
            return {
                "answer": format_not_found_response(result.intent),
                "items": [],
                "sources": [],
                "confidence": 0.0,
                "found": False,
                "intent": result.intent.value,
                "used_graph": result.used_graph,
            }

        # Если граф вернул структурированные items — форматируем их
        if result.items and result.used_graph:
            formatted = renderer.render_items(result.items, result.intent)
            return {
                "answer": formatted,
                "items": result.items,
                "sources": result.sources,
                "confidence": result.confidence,
                "found": True,
                "intent": result.intent.value,
                "used_graph": result.used_graph,
            }

    # Default behavior (v1 or hybrid search result)
    return {
        "answer": result.evidence,
        "items": result.items,
        "sources": result.sources,
        "confidence": result.confidence,
        "found": result.found,
        "intent": result.intent.value,
        "used_graph": result.used_graph,
    }
