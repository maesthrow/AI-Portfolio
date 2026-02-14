"""CV sending graph nodes.

Explicit nodes for the CV/resume sending scenario.
Multi-turn email collection is managed via ``pending_action`` in
:class:`AgentState`, persisted across HTTP requests by the
StateGraph checkpointer.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from ..email.validation import extract_email, validate_email

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _emit_status(stage: str, text: str, config: RunnableConfig) -> None:
    """Put a status event onto the queue (same pattern as rag_tool.py)."""
    queue = (config.get("configurable") or {}).get("_status_queue")
    if queue is None:
        return
    try:
        queue.put_nowait({"stage": stage, "text": text})
    except Exception:
        pass


@dataclass
class _SendResult:
    """Wrapper for CV send outcome with user-facing message."""
    success: bool
    message: str


def _do_send_cv(email: str, config: RunnableConfig) -> _SendResult:
    """Validate, rate-limit, and send CV to *email*.

    Synchronous — called from async nodes via ``asyncio.to_thread``
    (except rate-limit checks which are fast Redis calls).
    """
    from ..deps import email_service, rate_limiter

    # 1. Validate
    is_valid, error = validate_email(email)
    if not is_valid:
        return _SendResult(success=False, message=f"Некорректный email: {error}. Укажите другой адрес.")

    # 2. Check email service availability
    svc = email_service()
    if not svc.available:
        return _SendResult(
            success=False,
            message="Сервис отправки email временно недоступен. Попробуйте позже.",
        )

    # 3. CV-specific rate limit (separate from token rate limit)
    client_ip = (config.get("configurable") or {}).get("_client_ip", "unknown")
    if not _check_cv_rate_limit(client_ip, email):
        return _SendResult(
            success=False,
            message="Превышен лимит отправок CV. Попробуйте позже.",
        )

    # 4. Send
    _emit_status("sending_cv", "Отправляю резюме...", config)
    result = svc.send_cv(email)

    if result.success:
        _record_cv_send(client_ip, email)
        return _SendResult(success=True, message=result.message)

    logger.error("CV send failed: %s", result.error)
    return _SendResult(success=False, message=result.message)


def _get_cv_redis():
    """Get Redis client for CV rate limiting (graceful degradation)."""
    from ..deps import rate_limiter
    try:
        return rate_limiter()._get_redis()
    except Exception:
        return None


def _check_cv_rate_limit(ip: str, email: str) -> bool:
    """Check Redis-based rate limit for CV sends.

    Returns True when the send is allowed.
    """
    from ..deps import settings

    redis_client = _get_cv_redis()
    if redis_client is None:
        return True  # Redis unavailable → graceful degradation

    s = settings()

    try:
        ip_key = f"cv:ip:{ip}"
        ip_count = int(redis_client.get(ip_key) or 0)
        if ip_count >= s.cv_send_limit_per_ip:
            logger.info("CV rate limit hit for IP %s (%d/%d)", ip, ip_count, s.cv_send_limit_per_ip)
            return False

        email_key = f"cv:email:{email.lower()}"
        email_count = int(redis_client.get(email_key) or 0)
        if email_count >= s.cv_send_limit_per_email:
            logger.info("CV rate limit hit for email %s (%d/%d)", email, email_count, s.cv_send_limit_per_email)
            return False
    except Exception as exc:
        logger.warning("CV rate limit check failed: %s", exc)
        return True  # Graceful degradation

    return True


def _record_cv_send(ip: str, email: str) -> None:
    """Record successful CV send in Redis for rate limiting."""
    from ..deps import settings

    redis_client = _get_cv_redis()
    if redis_client is None:
        return

    s = settings()
    window = s.cv_send_limit_window_seconds

    try:
        pipe = redis_client.pipeline()
        ip_key = f"cv:ip:{ip}"
        email_key = f"cv:email:{email.lower()}"

        pipe.incr(ip_key)
        pipe.expire(ip_key, window)
        pipe.incr(email_key)
        pipe.expire(email_key, window)
        pipe.execute()
    except Exception as exc:
        logger.warning("CV rate limit record failed: %s", exc)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


async def cv_start_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """Handle initial CV request.

    If the user included an email in their message → validate & send.
    Otherwise → ask for the email (set ``pending_action``).
    """
    messages = state.get("messages") or []
    last_msg = messages[-1]
    text: str = getattr(last_msg, "content", "") if hasattr(last_msg, "content") else str(last_msg)

    email = extract_email(text)

    if email:
        result = await asyncio.to_thread(_do_send_cv, email, config)
        return {
            "messages": [AIMessage(content=result.message)],
            "pending_action": "",
        }

    return {
        "messages": [AIMessage(content="На какой email отправить резюме Дмитрия?")],
        "pending_action": "cv_awaiting_email",
    }


async def cv_process_node(state: dict[str, Any], config: RunnableConfig) -> dict:
    """Process email response in multi-turn CV flow.

    The router has already confirmed we are in ``cv_awaiting_email`` state.
    Extract email, validate, and send.
    """
    messages = state.get("messages") or []
    last_msg = messages[-1]
    text: str = getattr(last_msg, "content", "") if hasattr(last_msg, "content") else str(last_msg)

    email = extract_email(text)

    if email:
        result = await asyncio.to_thread(_do_send_cv, email, config)
        return {
            "messages": [AIMessage(content=result.message)],
            "pending_action": "",
        }

    return {
        "messages": [AIMessage(content="Не удалось распознать email-адрес. Пожалуйста, укажите корректный email.")],
        "pending_action": "cv_awaiting_email",
    }
