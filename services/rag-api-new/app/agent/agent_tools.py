"""LangChain tools used by the agent graph.

Named `agent_tools.py` to avoid collision with the `tools/` package
(`app/agent/tools/`) which contains plan-executor helpers.
"""

from __future__ import annotations

import logging

from langchain.tools import tool

from ..deps import settings, vectorstore
from ..rag.core import portfolio_rag_answer
from ..utils.logging_utils import truncate_text

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@tool("portfolio_rag_tool")
def portfolio_rag_tool(question: str) -> dict:
    """
    Получить ответ из портфолио разработчика Дмитрия Каргина через RAG.
    Всегда использовать для вопросов о проектах, компаниях, технологиях, опыте, достижениях и документах.
    """
    logger.info("portfolio_rag_tool called question=%r", question)
    result = portfolio_rag_answer(question=question)
    if isinstance(result, dict):
        logger.info(
            "portfolio_rag_tool result found=%s confidence=%s sources=%s answer_preview=%r",
            result.get("found"),
            result.get("confidence"),
            len(result.get("sources") or []) if isinstance(result.get("sources"), list) else None,
            truncate_text(result.get("answer"), limit=400),
        )
    return result


@tool("list_projects_tool")
def list_projects_tool(limit: int = 10) -> str:
    """
    Кратко перечисляет основные проекты и компании из портфолио разработчика Дмитрия Каргина.
    """
    s = settings()
    vs = vectorstore(s.chroma_collection)

    # Берём несколько документов типа 'project'
    docs = vs.similarity_search("проекты разработчика", k=limit, filter={"type": "project"})
    logger.info("list_projects_tool retrieved docs=%d limit=%d", len(docs or []), limit)
    seen = set()
    lines: list[str] = []
    for d in docs:
        md = d.metadata or {}
        proj = md.get("name") or md.get("title")
        comp = md.get("company_name") or md.get("company")
        key = (proj, comp)
        if key in seen:
            continue
        seen.add(key)
        if proj:
            if comp:
                lines.append(f"- {proj} (компания: {comp})")
            else:
                lines.append(f"- {proj}")

    if not lines:
        return "У меня нет информации о проектах в базе портфолио."

    return "Некоторые проекты Дмитрия Каргина:\n" + "\n".join(lines)
