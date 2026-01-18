"""
Rewrite LLM node for RAG agent.

Rewrites the answer when grounding verification detects:
- Ungrounded entities (hallucinations)
- Speculation markers

Uses LLM to rewrite the answer without ungrounded entities,
preserving the original meaning and structure.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from app.utils.logging_utils import truncate_text

if TYPE_CHECKING:
    from app.agent.state import RAGState

logger = logging.getLogger(__name__)


REWRITE_SYSTEM_PROMPT = """Ты — редактор ответов для AI-ассистента портфолио.

Твоя задача: переписать ответ, убрав из него все упоминания сущностей
(технологий, проектов, компаний), которых нет в списке известных.

ПРАВИЛА:
1. Сохрани структуру и смысл ответа
2. Удали только неподтверждённые сущности, не добавляй новые
3. Если после удаления ответ теряет смысл — скажи "информация не найдена"
4. Не добавляй извинения или объяснения почему что-то удалено
5. Говори о Дмитрии в третьем лице

ЗАПРЕЩЕНО:
- Выдумывать информацию
- Добавлять новые сущности
- Упоминать что ответ был переписан
"""


REWRITE_USER_TEMPLATE = """Исходный ответ:
{answer}

Сущности без подтверждения (нужно убрать):
{ungrounded_entities}

Известные сущности (можно использовать):
- Технологии: {technologies}
- Компании: {companies}
- Проекты: {projects}
- Роли: {roles}

Перепиши ответ, убрав неподтверждённые сущности.
"""


def rewrite_llm_node(state: RAGState) -> dict:
    """
    Rewrite answer to remove ungrounded entities.

    Called when grounding_action is "rewrite".
    For "refuse" action, returns a safe fallback response.

    Args:
        state: Current RAGState with answer, grounding_result, fact_bundle

    Returns:
        Partial state update with:
        - answer: Rewritten answer
    """
    answer = state.get("answer", "")
    grounding_result = state.get("grounding_result")
    grounding_action = state.get("grounding_action", "accept")
    fact_bundle = state.get("fact_bundle")

    logger.info(
        f"Rewrite: action={grounding_action}, "
        f"ungrounded={grounding_result.ungrounded_entities if grounding_result else []}"
    )

    # Handle refuse action with safe response
    if grounding_action == "refuse":
        safe_response = (
            "На основе имеющихся данных портфолио не удалось "
            "найти достоверную информацию по этому запросу."
        )
        logger.info("Rewrite: refusing with safe response")
        return {"answer": safe_response}

    # No rewrite needed
    if grounding_action == "accept" or not grounding_result:
        return {"answer": answer}

    # If grounding provided a suggested rewrite (from removing speculation)
    if grounding_result.suggested_rewrite and grounding_result.suggested_rewrite.strip():
        # Check if suggested rewrite is reasonable (not just a fallback)
        if len(grounding_result.suggested_rewrite) > 50:
            logger.info("Rewrite: using grounding's suggested_rewrite")
            return {"answer": grounding_result.suggested_rewrite}

    # Use LLM for complex rewrite
    ungrounded = grounding_result.ungrounded_entities or []

    # Prepare known entities
    technologies = []
    companies = []
    projects = []
    roles = []

    if fact_bundle:
        technologies = fact_bundle.technologies[:20]  # Limit for prompt size
        companies = fact_bundle.companies[:10]
        projects = fact_bundle.projects[:15]
        roles = fact_bundle.roles[:10]

    user_prompt = REWRITE_USER_TEMPLATE.format(
        answer=answer,
        ungrounded_entities=", ".join(ungrounded) if ungrounded else "нет",
        technologies=", ".join(technologies) if technologies else "нет данных",
        companies=", ".join(companies) if companies else "нет данных",
        projects=", ".join(projects) if projects else "нет данных",
        roles=", ".join(roles) if roles else "нет данных",
    )

    messages = [
        SystemMessage(content=REWRITE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    try:
        # Lazy import to avoid circular imports
        from app.deps import answer_llm
        llm = answer_llm()
        response = llm.invoke(messages)
        rewritten = response.content.strip()

        logger.info(
            f"Rewrite: LLM rewrite done, len={len(rewritten)}, "
            f"preview={truncate_text(rewritten, limit=200)}"
        )

        return {"answer": rewritten}

    except Exception as e:
        logger.error(f"Rewrite LLM failed: {e}")
        # Use suggested rewrite or fallback
        if grounding_result.suggested_rewrite:
            return {"answer": grounding_result.suggested_rewrite}
        return {
            "answer": "На основе имеющихся данных портфолио "
                     "не удалось сформировать ответ."
        }
