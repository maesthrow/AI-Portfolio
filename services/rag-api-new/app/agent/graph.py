from __future__ import annotations

from typing import List

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from ..rag.prompting import make_system_prompt

# ⚙️ Специальный промпт именно для АГЕНТА-ОРКЕСТРАТОРА (не для финального ответа)
AGENT_SYSTEM_PROMPT = """
ТВОЯ РОЛЬ:
- Планировать и вызывать инструменты.
- Никогда не придумывать факты о проектах, компаниях, деятельности, технологиях, достижениях и документах.

ЖЁСТКИЕ ПРАВИЛА:
1) Если вопрос касается:
   - разработчика Дмитрия
   - проектов,
   - компаний,
   - деятельности,
   - обязанностей,
   - достижений,
   - технологий/стека,
   - резюме/опыта работы,
   - документации по проектам,
   ТЫ ОБЯЗАН сначала вызвать инструмент `portfolio_rag_tool`.
   Отвечать на такие вопросы без обращения к `portfolio_rag_tool` строго запрещено.

2) Если пользователь просит перечислить проекты или технологии в целом,
   можно дополнительно использовать инструмент `list_projects_tool`.

3) Без инструментов можно отвечать только на:
   - приветствия ("привет", "здравствуй", "как дела"),
   - вопросы идентичности ("кто ты", "что ты умеешь", "зачем ты нужен").
   В этих случаях дай короткий ответ и не используй инструменты.

4) Если `portfolio_rag_tool` вернул, что данных нет,
   честно скажи, что в портфолио нет такой информации, и не выдумывай.

5) Суммаризируй полученные от инструментов данные и давай итоговый ответ на исходный запрос пользователя.

Всегда строго следуй этим правилам, даже если тебе кажется, что ты и так знаешь ответ.
"""


def build_agent_graph():
    """
    ReAct-агент с памятью по thread_id (session_id) и жёстким требованием звать RAG-tool.
    """
    from .tools import portfolio_rag_tool, list_projects_tool
    from ..deps import chat_llm

    llm = chat_llm()
    system_prompt = f"{make_system_prompt(None)}\n\n{AGENT_SYSTEM_PROMPT}"
    checkpointer = MemorySaver()

    agent = create_agent(
        model=llm,  # голая модель, tools ей передаст сам create_react_agent
        tools=[portfolio_rag_tool, list_projects_tool],
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )

    return agent
