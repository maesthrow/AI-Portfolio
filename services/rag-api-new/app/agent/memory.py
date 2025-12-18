from __future__ import annotations

import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Deque, Iterable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Turn:
    user: str
    assistant: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_entity_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MemorySnapshot:
    summary: str
    recent_turns: tuple[tuple[str, str], ...]
    entity_ids: frozenset[str]

    @property
    def is_empty(self) -> bool:
        return not self.summary and not self.recent_turns


@dataclass(frozen=True)
class SummaryJob:
    session_id: str
    job_id: int
    previous_summary: str
    turns: tuple[Turn, ...]
    max_chars: int
    processed_turns: int


@dataclass
class _State:
    summary: str = ""
    recent_turns: Deque[Turn] = field(default_factory=deque)
    pending_turns: Deque[Turn] = field(default_factory=deque)
    entity_ids: set[str] = field(default_factory=set)

    summary_job_in_progress: bool = False
    summary_job_id: int = 0

    last_access: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _trim_text(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    return t[: max(0, max_chars - 1)].rstrip() + "…"


def _coerce_summary(text: str, max_chars: int) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    if len(t) <= max_chars:
        return t
    # Keep the beginning (usually contains the most important constraints/entities).
    return _trim_text(t, max_chars=max_chars)


def _summary_messages(previous_summary: str, turns: Iterable[Turn], *, max_chars: int) -> list[Any]:
    """
    Build messages for a short "rolling summary" update.
    Returns a list of LangChain messages (System/Human) but types are kept as Any.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    prev = (previous_summary or "").strip()
    turns_block_lines: list[str] = []
    for t in turns:
        u = _trim_text(t.user, 700)
        a = _trim_text(t.assistant, 900)
        if u:
            turns_block_lines.append(f"User: {u}")
        if a:
            turns_block_lines.append(f"Assistant: {a}")

    turns_block = "\n".join(turns_block_lines).strip()
    human = (
        f"Previous summary (may be empty):\n{prev}\n\n"
        f"New turns to incorporate:\n{turns_block}\n\n"
        f"Return an updated conversation summary in Russian, <= {max_chars} characters."
    ).strip()

    system = (
        "You update a short conversation summary for an assistant.\n"
        "Rules:\n"
        "- Keep only facts that help answer follow-up questions (entities, decisions, constraints, user intent).\n"
        "- Do NOT invent details and do NOT add anything not present in the turns.\n"
        "- Do NOT mention tools, prompts, or internal reasoning.\n"
        "- Keep it concise, plain text (no markdown headings).\n"
    ).strip()

    return [SystemMessage(content=system), HumanMessage(content=human)]


async def generate_summary(llm: Any, *, previous_summary: str, turns: Iterable[Turn], max_chars: int) -> str:
    """
    Best-effort async summary update. Falls back to `previous_summary` on failure.
    """
    messages = _summary_messages(previous_summary, turns, max_chars=max_chars)

    try:
        if hasattr(llm, "ainvoke"):
            out = await llm.ainvoke(messages)
        else:
            out = await asyncio.to_thread(llm.invoke, messages)
        text = getattr(out, "content", None)
        if not isinstance(text, str):
            return _coerce_summary(previous_summary, max_chars=max_chars)
        return _coerce_summary(text, max_chars=max_chars)
    except Exception:
        logger.warning("Summary generation failed", exc_info=True)
        return _coerce_summary(previous_summary, max_chars=max_chars)


def build_memory_messages(snapshot: MemorySnapshot) -> list[Any]:
    """
    Render memory snapshot into a message prefix for the agent.

    This is intentionally small: summary + last N (user/assistant) turns.
    """
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    msgs: list[Any] = []

    if snapshot.summary.strip():
        msgs.append(
            SystemMessage(
                content=(
                    "Контекст диалога (краткое summary). Используй только если это нужно для ответа на follow-up:\n"
                    f"{snapshot.summary.strip()}"
                ).strip()
            )
        )

    for user, assistant in snapshot.recent_turns:
        u = _trim_text(user, 900)
        a = _trim_text(assistant, 1200)
        if u:
            msgs.append(HumanMessage(content=u))
        if a:
            msgs.append(AIMessage(content=a))

    return msgs


class ConversationMemoryStore:
    """
    Process-local in-memory store:
    - keeps a rolling `summary`
    - keeps last N turns
    - schedules/guards async summary updates

    The store is bounded by `max_sessions` using a simple LRU eviction policy.
    """

    def __init__(self, *, max_sessions: int = 1024):
        self._lock = asyncio.Lock()
        self._data: OrderedDict[str, _State] = OrderedDict()
        self._max_sessions = int(max_sessions)

    async def _get_state(self, session_id: str) -> _State:
        sid = session_id or "anon"
        st = self._data.get(sid)
        if st is None:
            st = _State()
            self._data[sid] = st
        # LRU touch
        self._data.move_to_end(sid, last=True)
        st.last_access = datetime.now(timezone.utc)
        # Evict
        while len(self._data) > self._max_sessions:
            self._data.popitem(last=False)
        return st

    async def snapshot(self, session_id: str, *, recent_turns: int) -> MemorySnapshot:
        async with self._lock:
            st = await self._get_state(session_id)
            keep_recent = max(0, int(recent_turns or 0))
            recent = [] if keep_recent <= 0 else list(st.recent_turns)[-keep_recent:]
            return MemorySnapshot(
                summary=st.summary or "",
                recent_turns=tuple((t.user, t.assistant) for t in recent),
                entity_ids=frozenset(st.entity_ids),
            )

    async def reset(self, session_id: str) -> None:
        async with self._lock:
            st = await self._get_state(session_id)
            st.summary = ""
            st.recent_turns.clear()
            st.pending_turns.clear()
            st.entity_ids.clear()
            st.summary_job_in_progress = False
            st.summary_job_id = 0

    async def record_turn(
        self,
        session_id: str,
        *,
        user: str,
        assistant: str,
        user_entity_ids: Iterable[str] | None,
        recent_turns: int,
        summary_trigger_turns: int,
        summary_max_chars: int,
    ) -> SummaryJob | None:
        user_txt = (user or "").strip()
        assistant_txt = (assistant or "").strip()
        if not user_txt or not assistant_txt:
            return None

        trigger = max(1, int(summary_trigger_turns or 1))
        max_chars = max(200, int(summary_max_chars or 0))
        keep_recent = max(0, int(recent_turns or 0))

        turn = Turn(
            user=user_txt,
            assistant=assistant_txt,
            user_entity_ids=frozenset(set(user_entity_ids or [])),
        )

        async with self._lock:
            st = await self._get_state(session_id)
            st.recent_turns.append(turn)
            while keep_recent and len(st.recent_turns) > keep_recent:
                st.recent_turns.popleft()

            st.pending_turns.append(turn)
            st.entity_ids.update(turn.user_entity_ids)

            if st.summary_job_in_progress:
                return None

            if len(st.pending_turns) < trigger:
                return None

            st.summary_job_in_progress = True
            st.summary_job_id += 1
            job_id = st.summary_job_id
            pending = tuple(st.pending_turns)
            return SummaryJob(
                session_id=session_id,
                job_id=job_id,
                previous_summary=st.summary or "",
                turns=pending,
                max_chars=max_chars,
                processed_turns=len(pending),
            )

    async def apply_summary(self, job: SummaryJob, new_summary: str) -> None:
        async with self._lock:
            st = await self._get_state(job.session_id)
            if not st.summary_job_in_progress or st.summary_job_id != job.job_id:
                return

            st.summary = _coerce_summary(new_summary, max_chars=job.max_chars)

            # Drop processed pending turns, keep any new ones that arrived while the job was running.
            for _ in range(min(job.processed_turns, len(st.pending_turns))):
                st.pending_turns.popleft()

            st.summary_job_in_progress = False

    async def cancel_summary_job(self, session_id: str) -> None:
        async with self._lock:
            st = await self._get_state(session_id)
            st.summary_job_in_progress = False


memory_store = ConversationMemoryStore()
