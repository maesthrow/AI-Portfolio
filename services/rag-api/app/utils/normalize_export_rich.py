# services/rag-api/app/utils/normalize_export_rich.py
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Tuple, Any, DefaultDict
from collections import defaultdict
import json, hashlib

from ..schemas.ingest_schema import (
    ExportPayload, ProjectExport, CompanyExport, TechnologyExport,
    AchievementExport, DocumentExport
)

# эмбед-модель даёт ~512 токенов; грубая оценка ~4 символа на токен для ru
MAX_CHARS = 900  # ~230–300 токенов

_sent_splitter = re.compile(r'(?<=[\.\!\?])\s+')


def _split_text(text: str, max_chars: int = MAX_CHARS) -> list[str]:
    text = re.sub(r'[ \t]+', ' ', text).strip()
    if len(text) <= max_chars:
        return [text]

    # 1) сначала по абзацам
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    def flush_buf():
        nonlocal buf
        b = buf.strip()
        if b:
            chunks.append(b)
        buf = ""

    for para in paragraphs:
        if len(para) <= max_chars:
            # попробуем добавить в буфер
            if len(buf) + (1 if buf else 0) + len(para) <= max_chars:
                buf = (buf + "\n" + para) if buf else para
            else:
                flush_buf()
                buf = para
        else:
            # параграф длинный — режем по предложениям
            sents = _sent_splitter.split(para)
            cur = ""
            for s in sents:
                s = s.strip()
                if not s:
                    continue
                if len(s) > max_chars:
                    if cur:
                        chunks.append(cur.strip())
                        cur = ""
                    for i in range(0, len(s), max_chars):
                        chunks.append(s[i:i+max_chars].strip())
                    continue
                if len(cur) + (1 if cur else 0) + len(s) <= max_chars:
                    cur = (cur + " " + s) if cur else s
                else:
                    if cur:
                        chunks.append(cur.strip())
                    cur = s
            if cur:
                chunks.append(cur.strip())

    flush_buf()

    # финальный контроль: дорежем, если вдруг > max_chars
    out: list[str] = []
    for ch in chunks:
        if len(ch) <= max_chars:
            out.append(ch)
        else:
            for i in range(0, len(ch), max_chars):
                out.append(ch[i:i+max_chars].strip())
    return [c for c in out if c]


def _sha1(obj: Any) -> str:
    s = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _mk(doc_type: str, ref_id: int | str, text: str, metadata: Dict[str, Any]) -> tuple[str, str, dict]:
    doc_id = f"{doc_type}:{ref_id}"
    base_for_hash = {"type": doc_type, "ref_id": ref_id, "text": text, "metadata": metadata}
    md = dict(metadata)
    md["type"] = doc_type
    md["ref_id"] = ref_id
    md["content_hash"] = _sha1(base_for_hash)
    return doc_id, text, md


def _mk_chunks(doc_type: str, ref_id: int | str, text: str, metadata: Dict[str, Any]):
    chunks = _split_text(text)
    if len(chunks) == 1:
        yield _mk(doc_type, ref_id, chunks[0], metadata)
        return
    parent_id = f"{doc_type}:{ref_id}"
    for i, ch in enumerate(chunks, 1):
        md = dict(metadata)
        md["parent_id"] = parent_id
        md["part"] = i
        yield _mk(doc_type, f"{ref_id}:c{i}", ch, md)


# --- локальные утилиты ---

def _join(items: List[str]) -> str:
    return ", ".join(items) if items else "—"


def _safe(s: str | None) -> str:
    return s or "—"


def _period_line(p: ProjectExport | None) -> str:
    if not p:
        return ""
    if p.period:
        return f"Период проекта: {p.period}."
    if p.period_start or p.period_end:
        return f"Период проекта: {p.period_start or '…'} — {p.period_end or 'наст.'}."
    return ""


def _kind_human(kind: str | None) -> str | None:
    if not kind:
        return None
    k = (kind or "").lower().strip()
    if k == "commercial":
        return "Коммерческий"
    if k == "personal":
        return "Личный"
    return kind


# --- основная сборка ---

def normalize_export_rich(payload: ExportPayload) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
    project_by_id: Dict[int, ProjectExport] = {p.id: p for p in payload.projects}
    company_by_id: Dict[int, CompanyExport] = {c.id: c for c in payload.companies}

    projects_by_company: DefaultDict[int, List[ProjectExport]] = defaultdict(list)
    for p in payload.projects:
        if p.company_id is not None:
            projects_by_company[p.company_id].append(p)

    projects_by_tech: DefaultDict[str, List[ProjectExport]] = defaultdict(list)
    for p in payload.projects:
        for t in p.technologies or []:
            projects_by_tech[t].append(p)

    achievements_by_project: DefaultDict[int, List[AchievementExport]] = defaultdict(list)
    for a in payload.achievements:
        achievements_by_project[a.project_id].append(a)

    documents_by_project: DefaultDict[int, List[DocumentExport]] = defaultdict(list)
    for d in payload.documents:
        if d.project_id is not None:
            documents_by_project[d.project_id].append(d)

    # --- Projects ---
    for p in payload.projects:
        company = company_by_id.get(p.company_id) if p.company_id is not None else None
        achs = achievements_by_project.get(p.id, [])
        docs = documents_by_project.get(p.id, [])

        kind_h = _kind_human(getattr(p, "kind", None))
        links_line_parts: list[str] = []
        if getattr(p, "repo_url", None):
            links_line_parts.append(f"Исходники: {p.repo_url}")
        if getattr(p, "demo_url", None):
            links_line_parts.append(f"Демо: {p.demo_url}")

        # Основной «фактовый» текст проекта
        lines = [
            f"Проект: {p.name}.",
            f"Компания: {company.name if company else '—'}.",
            _period_line(p),
            f"Технологии: {_join(p.technologies)}.",
            f"Описание: {_safe(p.description)}.",
        ]
        if kind_h:
            lines.append(f"Тип: {kind_h}.")
        if links_line_parts:
            lines.append(" ; ".join(links_line_parts))

        if achs:
            lines.append("Достижения:")
            for a in achs:
                lines.append(f" • {a.title}: {_safe(a.description)}.")
        if docs:
            lines.append("Документы проекта:")
            for d in docs[:10]:
                lines.append(f" • {d.title} ({_safe(d.doc_type)}): {d.url}")

        meta = {
            "name": p.name,
            "company_id": p.company_id,
            "company_name": p.company_name,
            "period": p.period,
            "period_start": p.period_start,
            "period_end": p.period_end,
            "technologies": p.technologies or [],
            "technology_names": p.technologies or [],  # дублируем ключ для удобства фильтров
            "achievement_ids": [a.id for a in achs],
            "document_ids": [d.id for d in docs],
            "url": p.url,
            # Новые поля проекта:
            "kind": (p.kind or "").lower() if getattr(p, "kind", None) else None,
            "weight": getattr(p, "weight", None),
            "repo_url": getattr(p, "repo_url", None),
            "demo_url": getattr(p, "demo_url", None),
        }
        yield from _mk_chunks("project", p.id, "\n".join([l for l in lines if l and l.strip()]), meta)

    # --- Achievements ---
    for a in payload.achievements:
        proj = project_by_id.get(a.project_id)
        company = company_by_id.get(proj.company_id) if proj and proj.company_id is not None else None
        techs = proj.technologies if proj else []

        text = "\n".join(filter(None, [
            f"Достижение: {a.title}.",
            f"Проект: {proj.name if proj else '—'} (компания: {company.name if company else '—'}).",
            _period_line(proj),
            f"Технологии проекта: {_join(techs)}.",
            f"Кратко: {_safe(a.description)}.",
            f"Ссылки: {_join(a.links)}."
        ]))

        meta = {
            "title": a.title,
            "project_id": a.project_id,
            "project_name": proj.name if proj else None,
            "company_id": proj.company_id if proj else None,
            "company_name": company.name if company else None,
            "technology_names": techs,
            "links": a.links or [],
        }
        yield from _mk_chunks("achievement", a.id, text, meta)

    # --- Technologies ---
    for t in payload.technologies:
        projs = projects_by_tech.get(t.name, [])
        proj_names = [p.name for p in projs]
        company_names = sorted({p.company_name for p in projs if p.company_name})

        text = "\n".join(filter(None, [
            f"Технология: {t.name}.",
            f"Алиасы: {_join(t.aliases)}.",
            f"Использовалась в проектах: {_join(proj_names)}.",
            f"Компании: {_join(company_names)}.",
            f"Подробнее: {_safe(t.url)}."
        ]))

        meta = {
            "name": t.name,
            "aliases": t.aliases or [],
            "project_ids": [p.id for p in projs],
            "project_names": proj_names,
            "company_ids": list({p.company_id for p in projs if p.company_id is not None}),
            "company_names": company_names,
            "url": t.url
        }
        yield from _mk_chunks("technology", t.id, text, meta)

    # --- Companies ---
    for c in payload.companies:
        projs = projects_by_company.get(c.id, [])
        text = "\n".join(filter(None, [
            f"Компания: {c.name}.",
            f"Описание: {_safe(c.description)}.",
            f"Сайт: {_safe(c.website)}.",
            f"Проекты: {_join([p.name for p in projs])}."
        ]))
        meta = {
            "name": c.name,
            "website": c.website,
            "project_ids": [p.id for p in projs],
            "project_names": [p.name for p in projs],
        }
        yield from _mk_chunks("company", c.id, text, meta)

    # --- Documents ---
    for d in payload.documents:
        proj = project_by_id.get(d.project_id) if d.project_id is not None else None
        company = company_by_id.get(d.company_id) if d.company_id is not None else None

        text = "\n".join(filter(None, [
            f"Документ: {d.title}.",
            f"Тип: {_safe(d.doc_type)}.",
            f"Проект: {proj.name if proj else '—'}; компания: {company.name if company else '—'}.",
            f"Аннотация: {_safe(d.summary)}.",
            f"Ссылка: {d.url}"
        ]))
        meta = {
            "title": d.title,
            "doc_type": d.doc_type,
            "project_id": d.project_id,
            "company_id": d.company_id,
            "project_name": proj.name if proj else None,
            "company_name": company.name if company else None,
            "url": d.url,
            "meta": d.meta or {},
        }
        yield from _mk_chunks("document", d.id, text, meta)

    # --- Catalog: все технологии с частотами по проектам ---
    all_tech_names = sorted(projects_by_tech.keys(), key=str.casefold)
    lines = ["Сводка технологий (всего):"]
    for tn in all_tech_names:
        cnt = len(projects_by_tech.get(tn, []))
        if cnt:
            lines.append(f" • {tn} — в {cnt} проектах")
    text = "\n".join(lines)

    meta = {
        "type": "catalog",
        "catalog_kind": "technologies_all",
        "technology_names": all_tech_names,
        "technology_counts": {tn: len(projects_by_tech.get(tn, [])) for tn in all_tech_names},
    }
    yield from _mk_chunks("catalog", "tech:all", text, meta)

    # --- Catalog: технологии по компаниям ---
    for c in payload.companies:
        projs = projects_by_company.get(c.id, [])
        tech_counter: dict[str, int] = {}
        for p in projs:
            for tn in (p.technologies or []):
                tech_counter[tn] = tech_counter.get(tn, 0) + 1

        if not tech_counter:
            continue

        ordered = sorted(tech_counter.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
        lines = [f"Сводка технологий компании: {c.name}"]
        for tn, cnt in ordered:
            lines.append(f" • {tn} — в {cnt} проектах")
        text = "\n".join(lines)

        meta = {
            "type": "catalog",
            "catalog_kind": "technologies_by_company",
            "company_id": c.id,
            "company_name": c.name,
            "technology_names": [tn for tn, _ in ordered],
            "technology_counts": dict(tech_counter),
        }
        yield from _mk_chunks("catalog", f"tech:company:{c.id}", text, meta)
