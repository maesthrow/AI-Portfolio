from __future__ import annotations

from fastapi import APIRouter

from app.rag.core import portfolio_rag_answer
from app.schemas.ask import AskRequest, AskResponse

router = APIRouter(prefix="/api/v1", tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    result = portfolio_rag_answer(
        question=req.question,
        k=req.k,
        collection=req.collection,
        extra_system=req.system_prompt,
    )
    return AskResponse(**result)
