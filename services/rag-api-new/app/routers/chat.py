from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator
from uuid import uuid4

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from app.deps import agent_app, rate_limiter, settings
from app.llm import get_provider_info
from app.rate_limit import TokenUsageCollector
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

    # === Input Length Validation (approximate tokens: ~4 chars per token) ===
    s = settings()
    approx_tokens = -(-len(req.question) // 4)  # ceil division
    if approx_tokens > s.max_user_input_tokens:
        async def validation_error_generator():
            yield json.dumps(
                {
                    "type": "error",
                    "error": "Message too long",
                    "detail": f"Максимальная длина сообщения ~{s.max_user_input_tokens} токенов (получено: ~{approx_tokens})"
                },
                ensure_ascii=False,
            ) + "\n"

        logger.warning(
            "Input validation failed: message too long message_id=%s approx_tokens=%d max_tokens=%d chars=%d",
            message_id,
            approx_tokens,
            s.max_user_input_tokens,
            len(req.question),
        )

        return StreamingResponse(
            validation_error_generator(),
            media_type="application/x-ndjson",
        )

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
            response, identity_usage = await generate_identity_response(req.question)
            yield json.dumps({"type": "delta", "content": response}, ensure_ascii=False) + "\n"

            # Create collector and add identity usage
            collector = TokenUsageCollector()
            if identity_usage:
                s = settings()
                provider, model = get_provider_info(s.identity_llm)
                collector.add("identity", provider, model, identity_usage)
                collector.log_summary(message_id)

            # Record in rate limiter
            final_rate_limit = None
            if limiter.settings.rate_limit_enabled and collector.total_tokens > 0:
                final_rate_limit = limiter.record_usage(client_ip, collector.total_tokens)
                logger.info(
                    "identity_generator rate_limit_recorded message_id=%s tokens=%d ip_used=%d/%d remaining=%d",
                    message_id,
                    collector.total_tokens,
                    final_rate_limit.ip.used,
                    final_rate_limit.ip.limit,
                    final_rate_limit.ip.remaining,
                )

            yield json.dumps(
                {
                    "type": "end",
                    "message_id": message_id,
                    "finish_reason": "stop",
                    "usage": collector.to_dict(),
                    "rate_limit": final_rate_limit.model_dump() if final_rate_limit else None,
                },
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
        # TokenUsageCollector for aggregating all LLM usage
        collector = TokenUsageCollector()
        agent_usage = None
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
                        agent_usage = getattr(chunk, "usage_metadata", None)
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
                            agent_usage = output.usage_metadata
                        elif hasattr(output, "response_metadata"):
                            rm = output.response_metadata or {}
                            if "token_usage" in rm:
                                agent_usage = rm["token_usage"]
                            elif "usage" in rm:
                                agent_usage = rm["usage"]

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

                    # Extract usage from rag_tool output
                    # tool_output can be: dict, str (JSON), or LangChain message with .content
                    parsed_output = None
                    if isinstance(tool_output, dict):
                        parsed_output = tool_output
                    elif isinstance(tool_output, str):
                        try:
                            parsed_output = json.loads(tool_output)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    elif hasattr(tool_output, "content"):
                        # LangChain ToolMessage or similar
                        content = tool_output.content
                        if isinstance(content, dict):
                            parsed_output = content
                        elif isinstance(content, str):
                            try:
                                parsed_output = json.loads(content)
                            except (json.JSONDecodeError, TypeError):
                                pass

                    if parsed_output and isinstance(parsed_output, dict) and "usage" in parsed_output:
                        tool_usage = parsed_output.get("usage") or {}
                        by_role = tool_usage.get("by_role") or {}
                        for role, role_data in by_role.items():
                            if isinstance(role_data, dict):
                                collector.add(
                                    role,
                                    role_data.get("provider", "unknown"),
                                    role_data.get("model", "unknown"),
                                    role_data,
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

        # === Add agent usage to collector ===
        if agent_usage:
            s = settings()
            provider, model = get_provider_info(s.agent_llm)
            collector.add("agent", provider, model, agent_usage)

        # Log usage summary
        collector.log_summary(message_id)

        # === Rate Limiting: записать usage ===
        final_rate_limit = None
        total_tokens = collector.total_tokens
        logger.info(
            "chat_stream usage message_id=%s total_tokens=%d breakdown=%s",
            message_id,
            total_tokens,
            collector.to_dict(),
        )
        if limiter.settings.rate_limit_enabled and total_tokens > 0:
            final_rate_limit = limiter.record_usage(client_ip, total_tokens)
            logger.info(
                "chat_stream rate_limit_recorded message_id=%s tokens=%d ip_used=%d/%d remaining=%d",
                message_id,
                total_tokens,
                final_rate_limit.ip.used,
                final_rate_limit.ip.limit,
                final_rate_limit.ip.remaining,
            )

        yield json.dumps(
            {
                "type": "end",
                "message_id": message_id,
                "usage": collector.to_dict(),
                "rate_limit": final_rate_limit.model_dump() if final_rate_limit else None,
            },
            ensure_ascii=False,
        ) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
