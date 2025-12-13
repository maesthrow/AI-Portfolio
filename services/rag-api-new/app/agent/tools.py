from __future__ import annotations
from langchain.tools import tool
from ..deps import vectorstore, settings
from ..rag.core import portfolio_rag_answer
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@tool("portfolio_rag_tool")
def portfolio_rag_tool(question: str) -> dict:
    """
    Получить ответ из портфолио разработчика Дмитрия Каргина через RAG.
    Всегда использовать для вопросов о проектах, компаниях, технологиях, опыте, достижениях и документах.
    """
    logger.info("portfolio_rag_tool called question=%r", question)
    return portfolio_rag_answer(question=question)


@tool("list_projects_tool")
def list_projects_tool(limit: int = 10) -> str:
    """
    Кратко перечисляет основные проекты и компании из портфолио разработчика Дмитрия Каргина.
    """
    s = settings()
    vs = vectorstore(s.chroma_collection)

    # Берём несколько документов типа 'project'
    docs = vs.similarity_search("проекты разработчика", k=limit, filter={"type": "project"})
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
