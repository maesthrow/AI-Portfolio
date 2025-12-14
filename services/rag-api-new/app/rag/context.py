from __future__ import annotations

from collections import defaultdict
import re
from typing import Iterable

from .evidence import pack_context
from .types import ScoredDoc

_KEY_CLEAN_RE = re.compile(r"[^\w]+", re.UNICODE)
_MD_BULLET_RE = re.compile(r"^\s*(?:[-\u2022*\u2013\u2014]|\d+[.)])\s+(.*)$", re.UNICODE)


def _normalize_key(value: str | None) -> str:
    txt = (value or "").casefold()
    txt = _KEY_CLEAN_RE.sub(" ", txt)
    return " ".join(txt.split()).strip()


def _extract_markdown_bullets(text: str | None) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []

    items: list[str] = []
    for line in raw.splitlines():
        ln = line.rstrip()
        if not ln.strip():
            continue
        m = _MD_BULLET_RE.match(ln)
        if m:
            val = (m.group(1) or "").strip()
            if val:
                items.append(val)
            continue
        if items and ln.startswith(("  ", "\t")):
            cont = ln.strip()
            if cont:
                items[-1] = f"{items[-1]} {cont}".strip()
    return [i for i in items if i]


def _infer_strategy(question: str) -> str:
    q = _normalize_key(question)

    achievements = ("достижен", "achievements", "achievement")
    contacts = ("контакт", "как связ", "email", "почт", "телефон", "github", "telegram", "tg", "ссылк")
    stats = ("статист", "цифр", "numbers", "stats")
    tags = ("тег", "tags", "tech focus", "технологическ фокус", "тех фокус")
    focus = ("фокус", "focus area", "сильн", "сильные", "направлен")
    work = ("подход", "approach", "как работа", "work approach")

    if any(t in q for t in achievements):
        return "ACHIEVEMENTS"
    if any(t in q for t in contacts):
        return "CONTACTS"
    if any(t in q for t in stats):
        return "STATS"
    if any(t in q for t in tags):
        return "TECH_TAGS"
    if any(t in q for t in focus):
        return "FOCUS_BULLETS"
    if any(t in q for t in work):
        return "WORK_BULLETS"
    return "COMPACT"


def _entity_matched(items: list[ScoredDoc], question: str, *, keys: Iterable[str]) -> list[ScoredDoc]:
    q = _normalize_key(question)
    if not q:
        return items

    def hit(md: dict) -> bool:
        for k in keys:
            v = md.get(k)
            if isinstance(v, str) and v and v in q:
                return True
        return False

    matched = [sd for sd in items if hit(sd.doc.metadata or {})]
    return matched if matched else items


def _strip_after(text: str, marker: str) -> str:
    if not text:
        return ""
    idx = text.casefold().find(marker.casefold())
    if idx < 0:
        return text
    return text[idx + len(marker) :].strip()


def _extract_after_label(text: str, label: str) -> str:
    if not text:
        return ""
    low = text.casefold()
    lab = label.casefold()
    idx = low.rfind(lab)
    if idx < 0:
        return text.strip()
    return text[idx + len(label) :].strip(" .:\n\t")


def _take_items(evidence: list[ScoredDoc], *, kinds: set[str]) -> list[ScoredDoc]:
    out: list[ScoredDoc] = []
    for sd in evidence:
        md = sd.doc.metadata or {}
        if md.get("type") != "item":
            continue
        if kinds and md.get("item_kind") not in kinds:
            continue
        out.append(sd)
    return out


def _append_line(lines: list[str], used: int, budget: int, line: str) -> int:
    if line == "" and not lines:
        return used
    if line == "" and lines and lines[-1] == "":
        return used
    add = len(line) + (1 if lines else 0)
    if used + add > budget:
        return used
    lines.append(line)
    return used + add


def _render_grouped(
    *,
    header: str,
    groups: list[tuple[str, list[str]]],
    budget: int,
    max_items: int,
) -> str:
    lines: list[str] = []
    used = 0
    used = _append_line(lines, used, budget, header)

    count_items = 0
    for title, items in groups:
        if not items:
            continue
        used = _append_line(lines, used, budget, "")
        used = _append_line(lines, used, budget, title)
        for it in items:
            if count_items >= max_items:
                break
            before = used
            used = _append_line(lines, used, budget, f"- {it}")
            if used == before:
                break
            count_items += 1
        if count_items >= max_items or used >= budget:
            break

    return "\n".join([l for l in lines if l is not None]).strip()


def _pack_achievements_from_items(question: str, items: list[ScoredDoc], *, budget: int, max_items: int) -> str:
    items = _entity_matched(
        items,
        question,
        keys=("project_slug_key", "project_name_key", "company_slug_key", "company_name_key"),
    )

    grouped: dict[str, list[tuple[int, float, str]]] = defaultdict(list)
    group_meta: dict[str, dict] = {}
    group_score: dict[str, float] = {}

    for sd in items:
        md = sd.doc.metadata or {}
        proj = (md.get("project_name") or md.get("project_slug") or "").strip()
        comp = (md.get("company_name") or md.get("company_slug") or "").strip()
        period = (md.get("period") or "").strip()

        if proj:
            g = proj
        elif comp:
            g = comp
        else:
            g = "Другое"

        group_meta.setdefault(g, {"project": proj or None, "company": comp or None, "period": period or None})
        bullet = _extract_after_label(sd.doc.page_content or "", "Достижение:")
        if not bullet:
            continue
        grouped[g].append((int(md.get("order_index") or 0), float(sd.score), bullet))
        group_score[g] = max(group_score.get(g, 0.0), float(sd.score))

    scored_groups: list[tuple[float, str, list[str]]] = []
    for g, triples in grouped.items():
        triples.sort(key=lambda x: (x[0] if x[0] > 0 else 10_000, -x[1], x[2].casefold()))
        uniq: list[str] = []
        seen = set()
        for _ord, _score, b in triples:
            key = _normalize_key(b)
            if not key or key in seen:
                continue
            seen.add(key)
            uniq.append(b)

        meta = group_meta.get(g) or {}
        title_parts = []
        if meta.get("project"):
            title_parts.append(f"Проект: {meta['project']}")
        elif g and g != "Другое":
            title_parts.append(f"Компания/контекст: {g}")
        else:
            title_parts.append("Контекст: прочее")
        if meta.get("company") and meta.get("project") and meta["company"] != meta["project"]:
            title_parts.append(f"Компания: {meta['company']}")
        if meta.get("period"):
            title_parts.append(f"Период: {meta['period']}")
        title = " | ".join([p for p in title_parts if p])

        scored_groups.append((float(group_score.get(g, 0.0)), title, uniq))

    scored_groups.sort(key=lambda x: (-x[0], -len(x[2]), x[1].casefold()))
    groups = [(title, items) for _score, title, items in scored_groups]
    return _render_grouped(header="Достижения (по данным из базы):", groups=groups, budget=budget, max_items=max_items)


def _pack_contacts_from_items(question: str, items: list[ScoredDoc], *, budget: int, max_items: int) -> str:
    items = _entity_matched(items, question, keys=("label_key", "kind_key", "value", "url"))

    triples: list[tuple[int, int, str]] = []
    for sd in items:
        md = sd.doc.metadata or {}
        is_primary = 1 if md.get("is_primary") else 0
        order = int(md.get("order_index") or 0)
        text = _extract_after_label(sd.doc.page_content or "", "Контакт:")
        if text:
            triples.append((is_primary, order, text))
    triples.sort(key=lambda x: (-x[0], x[1] if x[1] > 0 else 10_000, x[2].casefold()))
    out = [t[2] for t in triples]
    return _render_grouped(header="Контакты:", groups=[("Контакты Дмитрия", out)], budget=budget, max_items=max_items)


def _pack_stats_from_items(question: str, items: list[ScoredDoc], *, budget: int, max_items: int) -> str:
    items = _entity_matched(items, question, keys=("label_key", "key", "group_name"))

    triples: list[tuple[int, str]] = []
    for sd in items:
        md = sd.doc.metadata or {}
        order = int(md.get("order_index") or 0)
        text = _extract_after_label(sd.doc.page_content or "", "Статистика:")
        if text:
            triples.append((order, text))
    triples.sort(key=lambda x: (x[0] if x[0] > 0 else 10_000, x[1].casefold()))
    out = [t[1] for t in triples]
    return _render_grouped(header="Статистика:", groups=[("Ключевые цифры", out)], budget=budget, max_items=max_items)


def _pack_tags_from_items(question: str, items: list[ScoredDoc], *, budget: int, max_items: int) -> str:
    items = _entity_matched(items, question, keys=("tech_focus_label_key", "tag_name_key"))

    grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for sd in items:
        md = sd.doc.metadata or {}
        label = (md.get("tech_focus_label") or "").strip() or "Теги"
        tag = (md.get("tag_name") or "").strip()
        if not tag:
            tag = _extract_after_label(sd.doc.page_content or "", "Тег:")
        if not tag:
            continue
        grouped[label].append((int(md.get("order_index") or 0), tag))

    groups: list[tuple[str, list[str]]] = []
    for label, pairs in grouped.items():
        pairs.sort(key=lambda x: (x[0] if x[0] > 0 else 10_000, x[1].casefold()))
        uniq: list[str] = []
        seen = set()
        for _ord, tag in pairs:
            key = _normalize_key(tag)
            if not key or key in seen:
                continue
            seen.add(key)
            uniq.append(tag)
        groups.append((f"Фокус: {label}", uniq))

    groups.sort(key=lambda x: (-len(x[1]), x[0].casefold()))
    return _render_grouped(header="Теги и фокус (по данным из базы):", groups=groups, budget=budget, max_items=max_items)


def _pack_bullets_from_items(
    question: str,
    items: list[ScoredDoc],
    *,
    budget: int,
    max_items: int,
    kind: str,
) -> str:
    keys = ("focus_title_key",) if kind == "focus_bullet" else ("work_title_key",)
    items = _entity_matched(items, question, keys=keys)

    grouped: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for sd in items:
        md = sd.doc.metadata or {}
        title = (md.get("focus_title") if kind == "focus_bullet" else md.get("work_title")) or "Пункты"
        title = str(title).strip()
        bullet = _extract_after_label(sd.doc.page_content or "", "Пункт:")
        if not bullet:
            continue
        grouped[title].append((int(md.get("order_index") or 0), bullet))

    groups: list[tuple[str, list[str]]] = []
    for title, pairs in grouped.items():
        pairs.sort(key=lambda x: (x[0] if x[0] > 0 else 10_000, x[1].casefold()))
        uniq: list[str] = []
        seen = set()
        for _ord, b in pairs:
            key = _normalize_key(b)
            if not key or key in seen:
                continue
            seen.add(key)
            uniq.append(b)
        prefix = "Фокус" if kind == "focus_bullet" else "Подход"
        groups.append((f"{prefix}: {title}", uniq))

    groups.sort(key=lambda x: (-len(x[1]), x[0].casefold()))
    header = "Фокус (пункты):" if kind == "focus_bullet" else "Подход к работе (пункты):"
    return _render_grouped(header=header, groups=groups, budget=budget, max_items=max_items)


def _pack_achievements_from_docs(question: str, evidence: list[ScoredDoc], *, budget: int, max_items: int) -> str:
    out: dict[str, list[str]] = defaultdict(list)
    seen = set()

    # Если в вопросе явно есть сущность (по ключам метаданных), попробуем сначала оставить только совпадения.
    docs = [sd for sd in evidence if (sd.doc.metadata or {}).get("type") in {"experience_project", "experience"}]
    matched = _entity_matched(
        docs,
        question,
        keys=("project_slug_key", "project_name_key", "company_slug_key", "company_name_key"),
    )
    docs = matched or docs

    for sd in docs:
        md = sd.doc.metadata or {}
        t = md.get("type")

        raw = sd.doc.page_content or ""
        section = _strip_after(raw, "Достижения:")
        bullets = _extract_markdown_bullets(section)
        if not bullets:
            continue

        title = md.get("name") or md.get("company_name") or md.get("project_slug") or "Опыт/проект"
        title = str(title).strip()

        for b in bullets:
            hb = _normalize_key(b)
            if not hb or hb in seen:
                continue
            seen.add(hb)
            out[title].append(b)

    groups = [(f"Контекст: {k}", v) for k, v in out.items() if v]
    groups.sort(key=lambda x: (-len(x[1]), x[0].casefold()))
    return _render_grouped(header="Достижения (из секций документов):", groups=groups, budget=budget, max_items=max_items)


def pack_context_v2(
    question: str,
    evidence: list[ScoredDoc],
    *,
    char_budget: int,
    max_items: int,
) -> str:
    """
    Упаковщик контекста v2:
    - для вопросов про списки/пункты пытается отдать атомарные `type=item` (если есть),
      либо извлечь пункты из секций документов;
    - иначе использует текущий компактный pack_context.
    """
    budget = max(400, int(char_budget or 0))
    max_items = max(4, int(max_items or 0))
    strategy = _infer_strategy(question)

    if strategy == "COMPACT":
        return pack_context(evidence, token_budget=max(1, budget // 4))

    if strategy == "ACHIEVEMENTS":
        items = _take_items(evidence, kinds={"achievement"})
        if items:
            ctx = _pack_achievements_from_items(question, items, budget=budget, max_items=max_items)
            if ctx:
                return ctx
        ctx = _pack_achievements_from_docs(question, evidence, budget=budget, max_items=max_items)
        if ctx:
            return ctx

    if strategy == "CONTACTS":
        items = _take_items(evidence, kinds={"contact"})
        if items:
            ctx = _pack_contacts_from_items(question, items, budget=budget, max_items=max_items)
            if ctx:
                return ctx

    if strategy == "STATS":
        items = _take_items(evidence, kinds={"stat"})
        if items:
            ctx = _pack_stats_from_items(question, items, budget=budget, max_items=max_items)
            if ctx:
                return ctx

    if strategy == "TECH_TAGS":
        items = _take_items(evidence, kinds={"tech_tag"})
        if items:
            ctx = _pack_tags_from_items(question, items, budget=budget, max_items=max_items)
            if ctx:
                return ctx

    if strategy == "FOCUS_BULLETS":
        items = _take_items(evidence, kinds={"focus_bullet"})
        if items:
            ctx = _pack_bullets_from_items(question, items, budget=budget, max_items=max_items, kind="focus_bullet")
            if ctx:
                return ctx

    if strategy == "WORK_BULLETS":
        items = _take_items(evidence, kinds={"work_bullet"})
        if items:
            ctx = _pack_bullets_from_items(question, items, budget=budget, max_items=max_items, kind="work_bullet")
            if ctx:
                return ctx

    return pack_context(evidence, token_budget=max(1, budget // 4))
