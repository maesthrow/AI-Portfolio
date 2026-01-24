from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.deps import agent_app, rate_limiter
from app.schemas.chat import ChatRequest
from app.utils.logging_utils import compact_json, truncate_text

logger = logging.getLogger(__name__)

# Post-processing renderer (lazy import)
_format_renderer = None


def _get_format_renderer():
    """Lazy import of FormatRenderer to avoid circular imports."""
    global _format_renderer
    if _format_renderer is None:
        from app.rag.formatter import FormatRenderer
        _format_renderer = FormatRenderer()
    return _format_renderer


router = APIRouter(prefix="/api/v1", tags=["chat"])


def _get_client_ip(request: Request) -> str:
    """Получить реальный IP клиента (учитывая прокси)."""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip
    if request.client:
        return request.client.host
    return "unknown"


def _format_duration(seconds: int) -> str:
    """Форматировать секунды в человекочитаемый формат."""
    if seconds < 60:
        return f"{seconds} сек"
    minutes = (seconds + 59) // 60  # Округление вверх
    if minutes == 1:
        return "1 минуту"
    if minutes < 5:
        return f"{minutes} минуты"
    return f"{minutes} минут"


def _format_usage(raw: Any | None) -> dict[str, Any] | None:
    if not raw:
        return None

    # Поддержка dict и объектов с атрибутами (LangChain UsageMetadata)
    def _get(key: str, *alt_keys: str) -> int | None:
        # Сначала пробуем как dict
        if isinstance(raw, dict):
            for k in (key, *alt_keys):
                if k in raw and raw[k] is not None:
                    return int(raw[k])
        # Затем как объект с атрибутами
        else:
            for k in (key, *alt_keys):
                val = getattr(raw, k, None)
                if val is not None:
                    return int(val)
        return None

    prompt_tokens = _get("prompt_tokens", "input_tokens")
    completion_tokens = _get("completion_tokens", "output_tokens")
    total_tokens = _get("total_tokens")

    if total_tokens is None and (prompt_tokens is not None or completion_tokens is not None):
        total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

    # Если ничего не нашли
    if prompt_tokens is None and completion_tokens is None and total_tokens is None:
        return None

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


@router.post("/agent/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    # === Rate Limiting ===
    limiter = rate_limiter()

    # Проверка доступности Redis (если rate_limit включен)
    if not limiter.available:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "AI-агент временно недоступен. Попробуйте позже"
            }
        )

    # Получить идентификаторы
    client_ip = _get_client_ip(request)
    session_id = req.session_id or "anon"

    # Проверка лимита ДО обработки
    if limiter.settings.rate_limit_enabled:
        allowed, rate_limit_info = limiter.check_limit(client_ip)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": "Достигнут лимит использования AI-агента",
                    "details": {
                        "exceeded": rate_limit_info.exceeded,
                        "reset_in_seconds": rate_limit_info.reset_in_seconds,
                        "reset_in_human": _format_duration(rate_limit_info.reset_in_seconds)
                    }
                }
            )

    agent = agent_app()

    message_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    thread_id = session_id
    config = {"configurable": {"thread_id": thread_id}}

    question = req.question
    if req.system_prompt:
        question = f"{question}\n\nДоп. инструкции: {req.system_prompt.strip()}"

    logger.info(
        "chat_stream start message_id=%s thread_id=%s question=%r",
        message_id,
        thread_id,
        truncate_text(question, limit=800),
    )

    # === Fast path for identity questions (semantic matching) ===
    from app.agent.identity import is_identity_question, generate_identity_response

    is_identity, similarity = is_identity_question(req.question)
    if is_identity:
        logger.info("Identity question detected (similarity=%.3f): %r", similarity, req.question)

        async def identity_generator():
            yield json.dumps(
                {"type": "start", "message_id": message_id, "created_at": created_at},
                ensure_ascii=False,
            ) + "\n"
            # Генерируем ответ через LLM
            response = await generate_identity_response(req.question)
            yield json.dumps({"type": "delta", "content": response}, ensure_ascii=False) + "\n"
            yield json.dumps(
                {"type": "end", "message_id": message_id, "finish_reason": "stop"},
                ensure_ascii=False,
            ) + "\n"

        return StreamingResponse(
            identity_generator(),
            media_type="application/x-ndjson",
        )

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
                    # Извлечь usage из on_chat_model_end (GigaChat передаёт его здесь)
                    if kind == "on_chat_model_end" and output:
                        # LangChain AIMessage может содержать usage_metadata или response_metadata
                        if hasattr(output, "usage_metadata") and output.usage_metadata:
                            usage = output.usage_metadata
                        elif hasattr(output, "response_metadata"):
                            rm = output.response_metadata or {}
                            if "token_usage" in rm:
                                usage = rm["token_usage"]
                            elif "usage" in rm:
                                usage = rm["usage"]

                elif kind == "on_tool_start":
                    tool_name = event.get("name") or (event.get("data") or {}).get("name") or "tool"
                    data = event.get("data") or {}
                    tool_input = data.get("input") or data.get("inputs") or data.get("tool_input")
                    logger.info(
                        "tool_start message_id=%s thread_id=%s tool=%s input=%s",
                        message_id,
                        thread_id,
                        tool_name,
                        compact_json(tool_input, limit=2000),
                    )
                    yield json.dumps({"type": "tool_start", "tool": tool_name}, ensure_ascii=False) + "\n"

                elif kind == "on_tool_end":
                    data = event.get("data") or {}
                    tool_output = data.get("output") or data.get("result")
                    logger.info(
                        "tool_end message_id=%s thread_id=%s output_preview=%r",
                        message_id,
                        thread_id,
                        truncate_text(tool_output, limit=800),
                    )
                    yield json.dumps({"type": "tool_end"}, ensure_ascii=False) + "\n"

        except Exception as exc:
            logger.exception("Agent streaming failed")
            yield json.dumps({"type": "error", "message": str(exc)}, ensure_ascii=False) + "\n"
            return

        # Post-process final text
        if final_text:
            renderer = _get_format_renderer()
            final_text = renderer.post_process(final_text)

        if not sent_delta and final_text:
            yield json.dumps({"type": "delta", "content": final_text}, ensure_ascii=False) + "\n"

        # === Rate Limiting: записать usage ===
        final_rate_limit = None
        formatted_usage = _format_usage(usage)
        logger.info(
            "chat_stream usage message_id=%s raw_usage=%r formatted=%r",
            message_id,
            usage,
            formatted_usage,
        )
        if limiter.settings.rate_limit_enabled and formatted_usage:
            total_tokens = formatted_usage.get("total_tokens") or 0
            if total_tokens > 0:
                final_rate_limit = limiter.record_usage(client_ip, total_tokens)
                logger.info(
                    "chat_stream rate_limit_recorded message_id=%s tokens=%d ip_used=%d",
                    message_id,
                    total_tokens,
                    final_rate_limit.ip.used,
                )

        yield json.dumps(
            {
                "type": "end",
                "message_id": message_id,
                "usage": _format_usage(usage),
                "rate_limit": final_rate_limit.model_dump() if final_rate_limit else None,
            },
            ensure_ascii=False,
        ) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
