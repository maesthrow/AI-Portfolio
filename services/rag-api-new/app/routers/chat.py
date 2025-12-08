from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.deps import chat_llm, reranker, settings, vectorstore
from app.rag.evidence import pack_context, select_evidence
from app.rag.prompting import build_messages_for_answer, build_messages_when_empty, make_system_prompt
from app.rag.rank import rerank
from app.rag.retrieval import HybridRetriever
from app.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["chat"])


def _format_usage(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    prompt_tokens = raw.get("prompt_tokens") or raw.get("input_tokens")
    completion_tokens = raw.get("completion_tokens") or raw.get("output_tokens")
    total_tokens = raw.get("total_tokens")
    if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def _prepare_messages(req: ChatRequest):
    cfg = settings()
    collection = req.collection or cfg.chroma_collection
    vs = vectorstore(collection)
    rr = reranker()
    sys_prompt = make_system_prompt(req.system_prompt)

    hybrid = HybridRetriever(vs, collection=collection)
    candidates_all = hybrid.retrieve(
        req.question,
        k_dense=max(req.k * 4, 40),
        k_bm=max(req.k * 4, 40),
        k_final=max(req.k * 3, req.k),
    )

    if not candidates_all:
        return build_messages_when_empty(sys_prompt, req.question), {"collection": collection, "found": 0}

    scored = rerank(rr, req.question, candidates_all)
    base = select_evidence(scored, req.question, k=req.k, min_k=max(req.k, 8))
    context = pack_context(base, token_budget=900)
    messages = build_messages_for_answer(sys_prompt, req.question, context)
    return messages, {"collection": collection, "found": len(candidates_all)}


async def _iterate_llm_chunks(llm, messages) -> AsyncIterator[Any]:
    if hasattr(llm, "astream"):
        async for chunk in llm.astream(messages):
            yield chunk
        return
    if hasattr(llm, "stream"):
        for chunk in llm.stream(messages):
            yield chunk
        return
    yield llm.invoke(messages)


async def llm_stream(req: ChatRequest) -> AsyncIterator[dict[str, Any]]:
    llm = chat_llm()
    messages, _ = _prepare_messages(req)

    async for chunk in _iterate_llm_chunks(llm, messages):
        text = getattr(chunk, "content", "") or ""
        usage = getattr(chunk, "usage_metadata", None) if hasattr(chunk, "usage_metadata") else None
        yield {"content": text, "usage": usage}


@router.post("/agent/chat/stream")
async def chat_stream(req: ChatRequest):
    message_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    async def event_generator():
        usage = None
        yield json.dumps({"type": "start", "message_id": message_id, "created_at": created_at}) + "\n"
        try:
            async for item in llm_stream(req):
                if item.get("usage"):
                    usage = item["usage"]
                content = item.get("content") or ""
                if content:
                    yield json.dumps({"type": "delta", "content": content}) + "\n"
        except Exception as exc:
            logger.exception("Streaming chat failed")
            yield json.dumps({"type": "error", "message": str(exc)}) + "\n"
            return

        yield json.dumps(
            {"type": "end", "message_id": message_id, "usage": _format_usage(usage)}
        ) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
