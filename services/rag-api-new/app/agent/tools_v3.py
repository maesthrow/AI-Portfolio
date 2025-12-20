"""
Agent Tools v3 - full LLM-based RAG pipeline.

Implements the Planner LLM -> Executor -> Answer LLM pipeline
as specified in ТЗ TZ_Planner_Answer_LLM_rag-api-new.md.
"""
from __future__ import annotations

import logging
from langchain.tools import tool

from ..deps import settings

logger = logging.getLogger(__name__)


@tool("portfolio_rag_tool_v3")
def portfolio_rag_tool_v3(question: str) -> dict:
    """
    Полноценный RAG-инструмент с LLM-планированием.

    Пайплайн:
    1. Planner LLM анализирует вопрос и создаёт QueryPlan
    2. Executor выполняет tool_calls и собирает факты
    3. RenderEngine форматирует факты
    4. Answer LLM генерирует финальный ответ

    Используй для любых вопросов о портфолио:
    - проекты, компании, технологии
    - опыт работы, достижения
    - контакты, навыки

    Args:
        question: Вопрос о портфолио на русском или английском

    Returns:
        Словарь с полями:
        - answer: финальный ответ пользователю
        - rendered_facts: отформатированные факты
        - sources: источники информации
        - confidence: уверенность
        - found: найдены ли данные
        - intents: определённые намерения
    """
    cfg = settings()

    # Check feature flag
    if not cfg.planner_llm_v3:
        # Fallback to v2 tool
        logger.warning("planner_llm_v3 disabled, falling back to v2")
        from .tools_v2 import portfolio_rag_tool_v2
        return portfolio_rag_tool_v2.invoke(question)

    logger.info("portfolio_rag_tool_v3: question=%r", question[:100])

    # Import dependencies
    from ..deps import planner_llm, answer_llm
    from .planner import PlannerLLM
    from .executor import PlanExecutor
    from .render import RenderEngine
    from .answer import AnswerLLM

    try:
        # 1. Plan
        planner = PlannerLLM(planner_llm())
        plan = planner.plan(question)

        logger.info(
            "Plan created: intents=%s, entities=%d, tool_calls=%d, confidence=%.2f",
            [i.value for i in plan.intents],
            len(plan.entities),
            len(plan.tool_calls),
            plan.confidence,
        )

        # 2. Execute
        executor = PlanExecutor()
        payload = executor.execute(plan, question)

        logger.info(
            "Execution complete: found=%s, items=%d, confidence=%.2f",
            payload.found,
            len(payload.items),
            payload.meta.get("coverage", 0.0),
        )

        # 3. Render (deterministic)
        renderer = RenderEngine()
        rendered = renderer.render(
            facts=payload.items,
            style=payload.render_style,
            intents=payload.intents,
            max_items=plan.limits.max_items,
        )

        # 4. Answer (LLM)
        answer_gen = AnswerLLM(answer_llm())
        answer = answer_gen.generate(payload)

        return {
            "answer": answer,
            "rendered_facts": rendered,
            "items": [item.model_dump() for item in payload.items],
            "sources": [src.model_dump() for src in payload.sources],
            "confidence": payload.meta.get("coverage", 0.0),
            "found": payload.found,
            "intents": [i.value for i in payload.intents],
            "warnings": payload.warnings,
        }

    except Exception as e:
        logger.error("portfolio_rag_tool_v3 failed: %s", e, exc_info=True)

        # Fallback to v2 on error
        try:
            from .tools_v2 import portfolio_rag_tool_v2
            logger.warning("Falling back to v2 tool due to error")
            return portfolio_rag_tool_v2.invoke(question)
        except Exception as e2:
            logger.error("Fallback to v2 also failed: %s", e2)
            return {
                "answer": "Произошла ошибка при обработке запроса. Попробуйте переформулировать вопрос.",
                "rendered_facts": "",
                "items": [],
                "sources": [],
                "confidence": 0.0,
                "found": False,
                "intents": [],
                "warnings": [str(e)],
            }
