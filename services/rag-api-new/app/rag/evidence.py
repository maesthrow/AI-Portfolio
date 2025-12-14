from __future__ import annotations
from typing import Iterable, Tuple
from .nlp import keywords
from .types import Doc, ScoredDoc
from .entities import normalize_key, EntityMatch


def _kw_bonus(text: str, keys: list[str]) -> float:
    """Мягкий бонус за совпадения ключевых слов."""
    if not keys:
        return 0.0
    tl = (text or "").lower()
    hits = sum(1 for k in keys if k in tl)
    if hits == 0:
        return 0.0
    return min(0.20, 0.10 + 0.06 * (hits - 1))


def _meta_join(md: dict) -> str:
    parts: list[str] = []
    for k in (
        "title",
        "name",
        "slug",
        "project_slug",
        "technologies",
        "technology_names",
        "tags",
        "doc_type",
        "kind",
        "project_name",
        "company_name",
    ):
        v = md.get(k)
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, (list, tuple)):
            parts.extend(map(str, v))
    return " ".join(parts)


def _type_weight(md: dict) -> float:
    order = {
        "profile": 1.3,
        "experience": 1.2,
        "experience_project": 1.15,
        "project": 1.1,
        "item": 1.12,
        "technology": 1.0,
        "catalog": 0.98,
        "publication": 0.95,
        "focus_area": 0.95,
        "work_approach": 0.95,
    }
    t = (md or {}).get("type")
    return order.get(t, 1.0)


def _composite_score(sd: ScoredDoc, keys: list[str]) -> float:
    base = float(sd.score) * _type_weight(sd.doc.metadata or {})
    bonus = 0.0
    bonus += _kw_bonus(sd.doc.page_content or "", keys)
    bonus += 0.5 * _kw_bonus(_meta_join(sd.doc.metadata or {}), keys)
    return base * (1.0 + bonus)


def _dedup_key(d: Doc) -> Tuple[str | None, str | None]:
    md = d.metadata or {}
    if md.get("type") == "item":
        base = md.get("doc_id") or md.get("ref_id")
        return (str(base) if base is not None else None), None
    base = md.get("parent_id") or md.get("doc_id")
    if not base:
        t = md.get("type")
        ref = md.get("ref_id") or md.get("id") or md.get("source")
        if t and ref is not None:
            base = f"{t}:{ref}"
        else:
            base = ref
    return (str(base) if base is not None else None), md.get("part")


def _diversified_top(scored: list[ScoredDoc], keys: list[str], limit: int) -> list[ScoredDoc]:
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
    if not scored:
        return []

    keys = keywords(question)
    primary = _diversified_top(scored, keys, k)

    target = min_k if (min_k is not None) else k
    if len(primary) >= target:
        return primary

    pool = [(sd, _composite_score(sd, keys)) for sd in scored]
    pool.sort(key=lambda x: x[1], reverse=True)
    seen = {_dedup_key(sd.doc) for sd in primary}
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
    Формируем компактный контекст: заголовок [type] title и 1–2 предложения текста.
    """
    import re

    def _sents(text: str) -> list[str]:
        sents = re.split(r"(?<=[\.\!\?])\s+", text or "")
        sents = [s.strip() for s in sents if s and s.strip()]
        return sents or ([text.strip()] if text else [])

    def _title(md: dict) -> str:
        title = md.get("name") or md.get("title") or md.get("label") or md.get("kind") or md.get("type")
        ttype = md.get("type")
        if title and ttype:
            return f"[{ttype}] {title}"
        if title:
            return str(title)
        return f"[{ttype}]" if ttype else ""

    char_budget = token_budget * 4
    out_parts: list[str] = []
    used = 0
    for sd in evidence:
        md = sd.doc.metadata or {}
        sents = _sents(sd.doc.page_content)
        chunk = " ".join(sents[:2]).strip()
        if not chunk:
            continue
        header = _title(md)
        block = f"{header}: {chunk}" if header else chunk
        add = len(block) + 2
        if used + add > char_budget:
            break
        out_parts.append(block)
        used += add
    return "\n\n".join(out_parts)


def _md_str_values(md: dict, keys: tuple[str, ...]) -> list[str]:
    out: list[str] = []
    for k in keys:
        v = md.get(k)
        if isinstance(v, str) and v.strip():
            out.append(v.strip())
        elif isinstance(v, list):
            out.extend([str(x).strip() for x in v if str(x).strip()])
    return out


def _entity_match_score(md: dict, ent: EntityMatch) -> float:
    kind = ent.kind
    slug = (ent.slug or "").strip()
    key = ent.key

    if kind == "project":
        slug_vals = _md_str_values(md, ("project_slug", "slug"))
        key_vals = _md_str_values(md, ("project_slug_key", "project_name_key"))
        name_vals = _md_str_values(md, ("project_name", "name", "title"))
    elif kind == "company":
        slug_vals = _md_str_values(md, ("company_slug",))
        key_vals = _md_str_values(md, ("company_slug_key", "company_name_key"))
        name_vals = _md_str_values(md, ("company_name", "company", "name"))
    elif kind == "technology":
        slug_vals = _md_str_values(md, ("slug",))
        key_vals = _md_str_values(md, ("slug", "name"))
        name_vals = _md_str_values(md, ("name", "title"))
    else:
        return 0.0

    if slug:
        slug_norm = normalize_key(slug)
        for v in slug_vals:
            if normalize_key(v) == slug_norm:
                return 1.0
        for v in key_vals:
            if normalize_key(v) == slug_norm:
                return 1.0

    if key:
        for v in key_vals:
            if normalize_key(v) == key:
                return 0.9
        for v in name_vals:
            vn = normalize_key(v)
            if vn == key:
                return 0.75
            if key and vn and (key in vn or vn in key):
                return 0.55

    return 0.0


def apply_entity_policy(
    scored: list[ScoredDoc],
    *,
    entities: list[EntityMatch] | None,
    policy: str,
    scope_types: set[str] | None = None,
) -> list[ScoredDoc]:
    """
    Entity-aware post-processing поверх reranker-скоринга.

    - strict: отфильтровать документы "вне сущности" (но не трогать типы вне scope_types).
    - boost: слегка поднять score документам, которые матчятся по сущности.

    Всегда safe: если strict отрезал всё — вернуть исходный список.
    """
    if not scored or not entities or policy == "none":
        return scored

    scope = set(scope_types) if scope_types else None

    def in_scope(md: dict) -> bool:
        if not scope:
            return True
        t = md.get("type")
        return t in scope

    def match_score(md: dict) -> float:
        best = 0.0
        for e in entities:
            best = max(best, _entity_match_score(md, e) * float(e.score or 1.0))
        return best

    if policy == "strict":
        filtered: list[ScoredDoc] = []
        for sd in scored:
            md = sd.doc.metadata or {}
            if not in_scope(md):
                filtered.append(sd)
                continue
            if match_score(md) > 0.0:
                filtered.append(sd)
        return filtered if filtered else scored

    if policy == "boost":
        boosted: list[ScoredDoc] = []
        for sd in scored:
            md = sd.doc.metadata or {}
            if not in_scope(md):
                boosted.append(sd)
                continue
            m = match_score(md)
            if m <= 0.0:
                boosted.append(sd)
                continue
            factor = 1.0 + min(0.35, 0.18 + 0.25 * m)
            boosted.append(ScoredDoc(sd.doc, float(sd.score) * factor))
        boosted.sort(key=lambda x: x.score, reverse=True)
        return boosted

    return scored
