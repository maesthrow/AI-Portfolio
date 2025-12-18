from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.agent.followup import FollowUpContext, detect_follow_up
from app.agent.memory import build_memory_messages, generate_summary, memory_store
from app.deps import agent_app, chat_llm, settings
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


def _extract_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    content = getattr(obj, "content", None)
    if content is not None:
        return _extract_text(content)

    if isinstance(obj, dict):
        if "answer" in obj and isinstance(obj.get("answer"), str):
            return str(obj["answer"])
        if "content" in obj:
            return _extract_text(obj.get("content"))
        if "text" in obj:
            return _extract_text(obj.get("text"))
        if "output" in obj:
            return _extract_text(obj.get("output"))
        if "message" in obj:
            return _extract_text(obj.get("message"))
        if "messages" in obj:
            msgs = obj.get("messages") or []
            if isinstance(msgs, list) and msgs:
                return _extract_text(msgs[-1])
        if "generations" in obj:
            return _extract_text(obj.get("generations"))
        if "choices" in obj:
            return _extract_text(obj.get("choices"))
        return ""

    if isinstance(obj, (list, tuple)):
        parts = [_extract_text(x) for x in obj]
        parts = [p for p in parts if p]
        return "".join(parts)

    return ""


async def _iterate_agent_events(agent, state: dict[str, Any], config: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    """
    Prefer LangChain Runnable events (LangGraph/agents), but keep a safe fallback.
    """
    if hasattr(agent, "astream_events"):
        async for event in agent.astream_events(state, config=config, version="v2"):
            yield event
        return

    if hasattr(agent, "ainvoke"):
        result = await agent.ainvoke(state, config=config)
    else:
        result = agent.invoke(state, config=config)

    last = (result.get("messages") or [])[-1] if isinstance(result, dict) else None
    content = getattr(last, "content", None) if last is not None else None
    if content:
        yield {"event": "on_chat_model_stream", "data": {"chunk": type("Chunk", (), {"content": content})()}}


async def _run_summary_job(job) -> None:
    try:
        llm = chat_llm()
        summary = await generate_summary(
            llm,
            previous_summary=job.previous_summary,
            turns=job.turns,
            max_chars=job.max_chars,
        )
        await memory_store.apply_summary(job, summary)
    except Exception:
        logger.warning("Summary job failed", exc_info=True)
        try:
            await memory_store.cancel_summary_job(job.session_id)
        except Exception:
            pass


@router.post("/agent/chat/stream")
async def chat_stream(req: ChatRequest):
    agent = agent_app()

    message_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    cfg = settings()
    thread_id = req.session_id or "anon"
    config = {"configurable": {"thread_id": thread_id}}

    use_memory_v2 = bool(getattr(cfg, "agent_memory_v2", False))

    user_question = req.question
    question = req.question
    if req.system_prompt:
        question = f"{question}\n\nДоп. инструкции: {req.system_prompt.strip()}"

    followup_result = None
    if use_memory_v2:
        snapshot = await memory_store.snapshot(thread_id, recent_turns=cfg.agent_recent_turns)
        ctx = FollowUpContext(summary=snapshot.summary, recent_turns=snapshot.recent_turns, entity_ids=snapshot.entity_ids)
        followup_result = detect_follow_up(user_question, ctx, collection=cfg.chroma_collection)

        if not followup_result.is_follow_up:
            await memory_store.reset(thread_id)
            snapshot = await memory_store.snapshot(thread_id, recent_turns=cfg.agent_recent_turns)

        messages = []
        if followup_result.is_follow_up and not snapshot.is_empty:
            messages.extend(build_memory_messages(snapshot))
        messages.append(HumanMessage(content=question))

        state = {
            "messages": messages,
            "user_id": thread_id,
        }
    else:
        state = {
            "messages": [HumanMessage(content=question)],
            "user_id": req.session_id,
        }

    async def event_generator():
        usage = None
        sent_delta = False
        final_text = ""
        yield json.dumps(
            {"type": "start", "message_id": message_id, "created_at": created_at},
            ensure_ascii=False,
        ) + "\n"
        try:
            async for event in _iterate_agent_events(agent, state, config):
                kind = event.get("event")

                if kind == "on_chat_model_stream":
                    chunk = (event.get("data") or {}).get("chunk")
                    content = _extract_text(chunk)
                    if hasattr(chunk, "usage_metadata") and getattr(chunk, "usage_metadata", None):
                        usage = getattr(chunk, "usage_metadata", None)
                    if content:
                        sent_delta = True
                        final_text += content
                        yield json.dumps({"type": "delta", "content": content}, ensure_ascii=False) + "\n"

                elif kind in ("on_chat_model_end", "on_chain_end"):
                    data = event.get("data") or {}
                    output = data.get("output") if isinstance(data, dict) else None
                    text = _extract_text(output or data)
                    if text and not sent_delta:
                        final_text = text

                elif kind == "on_tool_start":
                    tool_name = event.get("name") or (event.get("data") or {}).get("name") or "tool"
                    yield json.dumps({"type": "tool_start", "tool": tool_name}, ensure_ascii=False) + "\n"

                elif kind == "on_tool_end":
                    yield json.dumps({"type": "tool_end"}, ensure_ascii=False) + "\n"

        except Exception as exc:
            logger.exception("Agent streaming failed")
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
            return

        if not sent_delta and final_text:
            yield json.dumps({"type": "delta", "content": final_text}, ensure_ascii=False) + "\n"

        if use_memory_v2 and final_text:
            try:
                job = await memory_store.record_turn(
                    thread_id,
                    user=user_question,
                    assistant=final_text,
                    user_entity_ids=getattr(followup_result, "question_entity_ids", None),
                    recent_turns=cfg.agent_recent_turns,
                    summary_trigger_turns=cfg.agent_summary_trigger_turns,
                    summary_max_chars=cfg.agent_summary_max_chars,
                )
                if job is not None:
                    asyncio.create_task(_run_summary_job(job))
            except Exception:
                logger.warning("Memory v2 update failed", exc_info=True)

        yield json.dumps(
            {"type": "end", "message_id": message_id, "usage": _format_usage(usage)},
            ensure_ascii=False,
        ) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
