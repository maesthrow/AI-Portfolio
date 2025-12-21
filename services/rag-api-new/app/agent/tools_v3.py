"""
Agent Tools v3 - full LLM-based RAG pipeline.

Implements the Planner LLM -> Executor -> Answer LLM pipeline
as specified in ТЗ TZ_Planner_Answer_LLM_rag-api-new.md.
"""
from __future__ import annotations

import logging
from langchain.tools import tool

from ..deps import settings
from ..utils.logging_utils import truncate_text

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
    logger.info("portfolio_rag_tool_v3: question=%r", question[:100])

    # Import dependencies
    from ..deps import planner_llm, answer_llm
    from .planner import PlannerLLM
    from .executor import PlanExecutor
    from .render import RenderEngine
    from .answer import AnswerLLM
    from .critic import CriticLLM, CriticDecision
    from .tools.portfolio_search_tool import execute_portfolio_search
    from .planner.schemas import SourceInfo

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

        # 2.1 Self-check: if retrieval is insufficient, run hybrid search and merge context
        try:
            if float(plan.confidence or 0.0) < 0.5:
                decision = CriticDecision(
                    sufficient=False,
                    need_search=True,
                    query=question,
                    reason="low_plan_confidence",
                )
                logger.info("Self-check forcing hybrid search due to low plan confidence=%.2f", float(plan.confidence or 0.0))
            else:
                critic = CriticLLM(planner_llm())
                decision = critic.evaluate(question, plan, payload)

            search_already_used = any(tc.tool == "portfolio_search_tool" for tc in (plan.tool_calls or []))
            if decision.need_search and not search_already_used:
                search_query = (decision.query or "").strip() or question
                logger.info("Self-check triggering portfolio_search_tool query=%r", truncate_text(search_query, limit=200))
                facts2, sources2, found2, confidence2, evidence2 = execute_portfolio_search(
                    query=search_query,
                    k=8,
                )

                if found2 and facts2:
                    merged_items = (payload.items or []) + facts2
                    payload.items = merged_items[: plan.limits.max_items]

                # Merge sources (dedupe by id)
                existing_ids = {s.id for s in (payload.sources or []) if s.id}
                for src in sources2:
                    if not isinstance(src, dict):
                        continue
                    try:
                        source_id = src.get("id")
                        if source_id is None:
                            source_id = src.get("ref_id") or src.get("source") or ""
                        label = src.get("label") or src.get("title") or src.get("name") or src.get("id") or source_id or ""
                        si = SourceInfo(id=str(source_id), label=str(label), type=src.get("type"))
                        if si.id and si.id not in existing_ids:
                            payload.sources.append(si)
                            existing_ids.add(si.id)
                    except Exception as e:
                        logger.warning("Self-check source merge failed: %s", e)

                if found2:
                    payload.found = True
                    payload.warnings.append("Self-check: использован дополнительный гибридный поиск")

                if isinstance(payload.meta, dict):
                    payload.meta["coverage"] = max(float(payload.meta.get("coverage") or 0.0), float(confidence2 or 0.0))
                    if evidence2:
                        payload.meta["evidence"] = evidence2

        except Exception as e:
            logger.warning("Self-check skipped due to error: %s", e)

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
