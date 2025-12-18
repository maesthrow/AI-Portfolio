from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

_WORD_RE = re.compile(r"[0-9A-Za-zА-Яа-яЁё_]+", re.UNICODE)


@dataclass(frozen=True)
class FollowUpContext:
    """
    Minimal conversation context for deterministic follow-up detection.

    - `recent_turns` contains the last N (user, assistant) pairs (already trimmed).
    - `entity_ids` is a union of entity ids seen in the current conversation context.
    """

    summary: str = ""
    recent_turns: tuple[tuple[str, str], ...] = ()
    entity_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FollowUpResult:
    is_follow_up: bool
    score: float
    reasons: tuple[str, ...] = ()
    question_entity_ids: frozenset[str] = frozenset()


_RESET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(забудь|забыть|неважно|не важно|другой вопрос|нов(ая|ая тема|ая тема)|с нуля)\b", re.IGNORECASE),
    re.compile(r"\b(reset|forget|ignore previous|new topic|start over)\b", re.IGNORECASE),
)

_GREETINGS: set[str] = {
    "привет",
    "здравствуй",
    "здравствуйте",
    "hello",
    "hi",
    "hey",
}

_FOLLOWUP_CONNECTORS: tuple[str, ...] = (
    "а",
    "и",
    "ещё",
    "еще",
    "так",
    "тогда",
    "кстати",
    "а ещё",
    "а еще",
    "и ещё",
    "и еще",
)

_FOLLOWUP_PHRASES: tuple[str, ...] = (
    "а там",
    "а тут",
    "а про это",
    "а про него",
    "а про неё",
    "а про нее",
    "а про них",
    "а в этом",
    "а в нём",
    "а в нем",
    "а в той",
    "а в том",
    "а какие там",
    "а что там",
    "а что насчет",
    "а что насчёт",
    "что насчет",
    "что насчёт",
)

_PRONOUN_REFERENCES: tuple[str, ...] = (
    "там",
    "тут",
    "здесь",
    "это",
    "этот",
    "эта",
    "эти",
    "то",
    "тот",
    "та",
    "те",
    "он",
    "она",
    "они",
    "его",
    "ее",
    "её",
    "их",
    "в этом",
    "в том",
    "в нём",
    "в нем",
    "про это",
    "об этом",
    "про него",
    "про нее",
    "про неё",
    "про них",
)

_SELF_CONTAINED_TOPICS: tuple[str, ...] = (
    "rag",
    "retrieval",
    "langchain",
    "langgraph",
    "языки",
    "язык",
    "language",
    "languages",
    "контакты",
    "contact",
    "contacts",
    "github",
    "email",
    "e-mail",
    "телеграм",
    "telegram",
    "linkedin",
    "где сейчас работает",
    "current job",
    "current position",
)

_TOPIC_WORDS: tuple[str, ...] = (
    "достижен",  # achievements stem
    "achievement",
    "контакт",
    "contact",
    "язык",
    "language",
    "проект",
    "project",
    "опыт",
)


def _norm(text: str) -> str:
    return " ".join((text or "").casefold().split()).strip()


def _tokens(text: str) -> list[str]:
    return [m.group(0).casefold() for m in _WORD_RE.finditer(text or "")]


def _starts_with_connector(q_norm: str) -> bool:
    for c in _FOLLOWUP_CONNECTORS:
        if q_norm == c or q_norm.startswith(f"{c} "):
            return True
    return False


def _has_any(q_norm: str, parts: Iterable[str]) -> bool:
    return any(p in q_norm for p in parts)


def _is_greeting(tokens: list[str]) -> bool:
    if not tokens:
        return False
    if len(tokens) == 1 and tokens[0] in _GREETINGS:
        return True
    joined = " ".join(tokens[:2])
    return joined in _GREETINGS


def _is_reset(q_norm: str) -> bool:
    return any(p.search(q_norm) for p in _RESET_PATTERNS)


def _is_short(tokens: list[str]) -> bool:
    return len(tokens) <= 5


def _is_self_contained(q_norm: str, *, entity_ids: frozenset[str]) -> bool:
    if entity_ids:
        return True
    return _has_any(q_norm, _SELF_CONTAINED_TOPICS)


def _extract_entity_ids(question: str, *, collection: str) -> frozenset[str]:
    """
    Entity-aware part of the follow-up detector.

    Best-effort: if Chroma/registry is unavailable, return an empty set and fall back to lexical heuristics.
    """
    try:
        from app.rag.entities import extract_entities, get_entity_registry

        registry = get_entity_registry(collection)
        ents = extract_entities(question, registry)
        return frozenset({e.id for e in ents if getattr(e, "id", None)})
    except Exception:
        return frozenset()


def detect_follow_up(
    question: str,
    ctx: FollowUpContext,
    *,
    collection: str,
    threshold: float = 1.6,
) -> FollowUpResult:
    q_norm = _norm(question)
    q_tokens = _tokens(question)

    entity_ids = _extract_entity_ids(question, collection=collection)

    if not q_norm:
        return FollowUpResult(
            is_follow_up=False,
            score=0.0,
            reasons=("empty_question",),
            question_entity_ids=entity_ids,
        )

    if not ctx.summary and not ctx.recent_turns:
        return FollowUpResult(
            is_follow_up=False,
            score=0.0,
            reasons=("no_history",),
            question_entity_ids=entity_ids,
        )

    if _is_greeting(q_tokens):
        return FollowUpResult(
            is_follow_up=False,
            score=0.0,
            reasons=("greeting",),
            question_entity_ids=entity_ids,
        )

    if _is_reset(q_norm):
        return FollowUpResult(
            is_follow_up=False,
            score=0.0,
            reasons=("explicit_reset",),
            question_entity_ids=entity_ids,
        )

    reasons: list[str] = []
    score = 0.0

    overlap = set(entity_ids) & set(ctx.entity_ids or frozenset())
    if overlap:
        score += 2.2
        reasons.append("entity_overlap")

    if _has_any(q_norm, _FOLLOWUP_PHRASES):
        score += 1.6
        reasons.append("followup_phrase")
    elif _starts_with_connector(q_norm):
        score += 0.6
        reasons.append("connector_prefix")

    if _has_any(q_norm, _PRONOUN_REFERENCES):
        score += 1.0
        reasons.append("pronoun_reference")

    if _is_short(q_tokens):
        score += 0.5
        reasons.append("short_question")

    # If the question is generic (e.g., "какие достижения?") but we already have a scoped context,
    # prefer treating it as follow-up to keep continuity.
    if not entity_ids and ctx.entity_ids and _has_any(q_norm, _TOPIC_WORDS):
        score += 1.2
        reasons.append("underspecified_with_topic_word")

    if _is_self_contained(q_norm, entity_ids=entity_ids):
        score -= 0.6
        reasons.append("self_contained")

    is_follow = score >= threshold
    return FollowUpResult(
        is_follow_up=is_follow,
        score=float(score),
        reasons=tuple(reasons),
        question_entity_ids=entity_ids,
    )
