from __future__ import annotations

import logging
from typing import List

from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage
from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver

from ..rag.prompting import make_system_prompt

logger = logging.getLogger(__name__)

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


AGENT_GRAPH_TOOL_PROMPT = """
ДОПОЛНИТЕЛЬНЫЙ ИНСТРУМЕНТ - graph_query_tool:
Используй для быстрого получения структурированных фактов:
- intent='achievements' - список достижений (entity_key = slug проекта/компании)
- intent='current_job' - текущее место работы
- intent='contacts' - контактная информация
- intent='languages' - языки программирования
- intent='technologies' - технологии (entity_key = slug проекта)
- intent='project_details', entity_key='<slug>' - детали конкретного проекта
- intent='experience' - опыт работы

Если graph_query_tool не нашёл данные (found=false), используй portfolio_rag_tool для полного поиска.
Предпочитай graph_query_tool для вопросов с конкретным проектом/компанией.
"""


def build_agent_graph():
    """
    ReAct-агент с памятью по thread_id (session_id) и жёстким требованием звать RAG-tool.

    При включённых feature flags:
    - rag_router_v2: использует portfolio_rag_tool_v2 вместо portfolio_rag_tool
    - agent_fact_tool + graph_rag_enabled: добавляет graph_query_tool
    """
    from .tools import portfolio_rag_tool, list_projects_tool
    from ..deps import chat_llm, settings

    cfg = settings()
    llm = chat_llm()
    checkpointer = MemorySaver()

    # Базовые инструменты
    tools = [portfolio_rag_tool, list_projects_tool]
    extra_prompt = ""

    # === Feature flags ===

    # rag_router_v2: заменяем portfolio_rag_tool на v2
    if cfg.rag_router_v2:
        from .tools_v2 import portfolio_rag_tool_v2
        tools = [portfolio_rag_tool_v2, list_projects_tool]
        logger.info("Agent using portfolio_rag_tool_v2 (rag_router_v2=true)")

    # agent_fact_tool + graph_rag_enabled: добавляем graph_query_tool
    if cfg.agent_fact_tool and cfg.graph_rag_enabled:
        from .tools_v2 import graph_query_tool
        tools.append(graph_query_tool)
        extra_prompt = AGENT_GRAPH_TOOL_PROMPT
        logger.info("Agent using graph_query_tool (agent_fact_tool=true, graph_rag_enabled=true)")

    # Формируем системный промпт
    system_prompt = f"{make_system_prompt(None)}\n\n{AGENT_SYSTEM_PROMPT}"
    if extra_prompt:
        system_prompt += extra_prompt

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )

    return agent
