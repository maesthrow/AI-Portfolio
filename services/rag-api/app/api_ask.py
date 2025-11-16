from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from .deps import agent_app, settings

router = APIRouter(tags=["ask"])


class AskReq(BaseModel):
    question: str
    k: int = 8
    collection: str | None = None
    system_prompt: str | None = None
    session_id: str | None = None  # важно для памяти


@router.post("/ask")
def ask(req: AskReq):
    agent = agent_app()
    cfg = settings()

    # состояние для графа
    state = {
        "messages": [HumanMessage(content=req.question)],
        "user_id": req.session_id,
    }

    # ключ для памяти
    thread_id = req.session_id or "anon"
    config = {"configurable": {"thread_id": thread_id}}

    result = agent.invoke(state, config=config)
    last = result["messages"][-1]

    # сейчас агент возвращает только текст ответа.
    # при желании можно парсить tool_calls и доставать источники из portfolio_rag_answer.
    return {
        "answer": last.content,
        "sources": [],            # можно будет прокинуть позже
        "found": 0,
        "collection": cfg.chroma_collection,
        "model": cfg.chat_model,
    }
