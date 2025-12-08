from __future__ import annotations
from typing import Iterable, Tuple
from .nlp import keywords
from .types import Doc, ScoredDoc


def _kw_bonus(text: str, keys: list[str]) -> float:
    """Мягкий бонус за совпадения ключей (и в тексте, и в метаданных). Без жёстких отсечек."""
    if not keys:
        return 0.0
    tl = (text or "").lower()
    hits = sum(1 for k in keys if k in tl)
    if hits == 0:
        return 0.0
    # убывающая отдача: 1 ключ = +10%, 2 = +16%, 3+ = +20% …
    return min(0.20, 0.10 + 0.06 * (hits - 1))


def _meta_join(md: dict) -> str:
    parts: list[str] = []
    for k in ("title","name","technologies","technology_names","tags","doc_type","kind","project_name","company_name"):
        v = md.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, tuple)):
            parts.extend(map(str, v))
    return " ".join(parts)


def _composite_score(sd: ScoredDoc, keys: list[str]) -> float:
    """Итоговый балл: reranker + бонусы за ключи в тексте и метаданных."""
    base = float(sd.score)
    bonus = 0.0
    bonus += _kw_bonus(sd.doc.page_content or "", keys)
    bonus += 0.5 * _kw_bonus(_meta_join(sd.doc.metadata or {}), keys)  # метаданные учитываем слабее
    return base * (1.0 + bonus)


def _dedup_key(d: Doc) -> Tuple[str | None, str | None]:
    md = d.metadata or {}
    return (md.get("parent_id") or md.get("ref_id") or md.get("id") or md.get("source")), md.get("part")


def _diversified_top(scored: list[ScoredDoc], keys: list[str], limit: int) -> list[ScoredDoc]:
    """Greedy-подбор по композитному скору с диверсификацией по parent/ref_id."""
    pool = [(sd, _composite_score(sd, keys)) for sd in scored]
    pool.sort(key=lambda x: x[1], reverse=True)

    seen = set()
    out: list[ScoredDoc] = []
    for sd, _cs in pool:
        key = _dedup_key(sd.doc)
        if key in seen:
            continue
        seen.add(key)
        out.append(sd)
        if len(out) >= limit:
            break
    return out


def select_evidence(scored: list[ScoredDoc], question: str, k: int, min_k: int | None = None) -> list[ScoredDoc]:
    """
    Универсальный отбор:
      - без жёсткого keyword-gate;
      - композитный ско́р (rerank + мягкий бонус ключей);
      - диверсификация по parent_id/ref_id;
      - гарантируем минимум источников min_k (если указано).
    """
    if not scored:
        return []

    keys = keywords(question)
    primary = _diversified_top(scored, keys, k)

    # если после отбора мало источников — добираем следующее по композитному баллу, не нарушая диверсификацию
    target = min_k if (min_k is not None) else k
    if len(primary) >= target:
        return primary

    # добор
    pool = [(sd, _composite_score(sd, keys)) for sd in scored]
    pool.sort(key=lambda x: x[1], reverse=True)
    seen = { _dedup_key(sd.doc) for sd in primary }
    out = list(primary)
    for sd, _cs in pool:
        key = _dedup_key(sd.doc)
        if key in seen:
            continue
        seen.add(key)
        out.append(sd)
        if len(out) >= target:
            break
    return out[:max(k, target)]


def pack_context(evidence: list[ScoredDoc], token_budget: int = 900) -> str:
    """
    Бюджетная упаковка контекста. Берём по 1–2 предложения каждого источника,
    пока не исчерпали бюджет символов (~4 симв/токен).
    """

    # импорт локально, чтобы не тянуть лишнее при старте
    import re

    def _sents(text: str) -> list[str]:
        sents = re.split(r'(?<=[\.\!\?])\s+', text or "")
        sents = [s.strip() for s in sents if s and s.strip()]
        return sents or ([text.strip()] if text else [])

    char_budget = token_budget * 4
    out_parts: list[str] = []
    used = 0
    for sd in evidence:
        sents = _sents(sd.doc.page_content)
        chunk = " ".join(sents[:2]).strip()
        if not chunk:
            continue
        add = len(chunk) + 2
        if used + add > char_budget:
            break
        out_parts.append(chunk)
        used += add
    return "\n\n".join(out_parts)
