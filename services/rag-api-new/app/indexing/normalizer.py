from __future__ import annotations

from collections import defaultdict
from datetime import date
import hashlib
from typing import Any, Iterable, Tuple

from .chunker import split_text
from ..schemas.export import (
    CompanyExperienceExport,
    ContactExport,
    ExperienceProjectExport,
    ExportPayload,
    FocusAreaExport,
    ProfileExport,
    ProjectExport,
    PublicationExport,
    StatExport,
    TechFocusExport,
    TechnologyExport,
    WorkApproachExport,
)
from ..utils.metadata import chunk_doc

NormalizedDoc = Tuple[str, str, dict[str, Any]]


def _stable_id(value: str) -> str:
    return hashlib.sha1((value or "").encode("utf-8")).hexdigest()[:12]


def _fix_text(value: str | None) -> str:
    """
    Defensive decoding against mojibake: try latin1->utf-8 if it looks broken.
    """
    if not value:
        return ""
    text = str(value)
    if "�" in text or "\ufffd" in text:
        try:
            text = text.encode("latin1").decode("utf-8")
        except Exception:
            pass
    return text.strip()


def _join_lines(parts: list[str | None]) -> str:
    cleaned: list[str] = []
    for p in parts:
        if p is None:
            continue
        txt = _fix_text(p)
        if txt:
            cleaned.append(txt)
    return "\n".join(cleaned)


def _period_line(start: date | None, end: date | None, is_current: bool) -> str:
    if not start and not end:
        return ""
    start_s = start.isoformat() if isinstance(start, date) else ""
    end_s = "present" if is_current and not end else (end.isoformat() if isinstance(end, date) else "")
    if start_s and end_s:
        return f"Период: {start_s} — {end_s}."
    if start_s:
        return f"Период: {start_s}."
    if end_s:
        return f"До: {end_s}."
    return ""


def _profile_docs(profile: ProfileExport) -> Iterable[NormalizedDoc]:
    text = _join_lines(
        [
            profile.full_name,
            profile.title,
            profile.subtitle,
            profile.current_position,
            profile.hero_headline,
            profile.hero_description,
            profile.summary_md,
        ]
    )
    if not text:
        return []
    meta = {
        "name": _fix_text(profile.full_name),
        "full_name": profile.full_name,
        "title": profile.title,
        "subtitle": profile.subtitle,
        "current_position": profile.current_position,
        "priority": "high",
    }
    return chunk_doc("profile", profile.id, text, meta, split_text)


def _experience_docs(exp: CompanyExperienceExport) -> Iterable[NormalizedDoc]:
    period = _period_line(exp.start_date, exp.end_date, exp.is_current)
    project_names = [_fix_text(p.name) for p in exp.projects]
    title_line = f"Опыт: {exp.role} @ {exp.company_name}" if exp.company_name else f"Опыт: {exp.role}"
    text = _join_lines(
        [
            title_line,
            period,
            f"Компания: {_fix_text(exp.company_name)}" if exp.company_name else None,
            f"О проекте/компании:\n{_fix_text(exp.company_summary_md)}" if exp.company_summary_md else None,
            f"Роль:\n{_fix_text(exp.company_role_md)}" if exp.company_role_md else None,
            f"Описание:\n{_fix_text(exp.summary_md)}" if exp.summary_md else None,
            f"Достижения:\n{_fix_text(exp.achievements_md)}" if exp.achievements_md else None,
            f"Проекты: {', '.join([p for p in project_names if p])}" if project_names else None,
        ]
    )
    if not text:
        return []
    meta = {
        "name": _fix_text(exp.company_name or exp.role),
        "company_name": exp.company_name,
        "company_slug": exp.company_slug,
        "company_url": exp.company_url,
        "start_date": exp.start_date.isoformat() if isinstance(exp.start_date, date) else None,
        "end_date": exp.end_date.isoformat() if isinstance(exp.end_date, date) else None,
        "is_current": exp.is_current,
        "kind": exp.kind,
        "project_ids": [p.id for p in exp.projects],
        "project_slugs": [p.slug for p in exp.projects if p.slug],
        "priority": "high",
    }
    return chunk_doc("experience", exp.id, text, meta, split_text)


def _experience_project_docs(
    exp: CompanyExperienceExport, proj: ExperienceProjectExport
) -> Iterable[NormalizedDoc]:
    text = _join_lines(
        [
            f"Проект: {_fix_text(proj.name)}" if proj.name else None,
            f"Компания: {_fix_text(exp.company_name)}" if exp.company_name else None,
            f"Период: {_fix_text(proj.period)}" if proj.period else None,
            f"Описание:\n{_fix_text(proj.description_md)}" if proj.description_md else None,
            f"Достижения:\n{_fix_text(proj.achievements_md)}" if proj.achievements_md else None,
        ]
    )
    if not text:
        return []
    meta = {
        "name": _fix_text(proj.name),
        "project_slug": proj.slug,
        "project_id": proj.id,
        "experience_id": exp.id,
        "company_name": exp.company_name,
        "company_slug": exp.company_slug,
        "period": proj.period,
    }
    return chunk_doc("experience_project", proj.id, text, meta, split_text)


def _project_docs(proj: ProjectExport) -> Iterable[NormalizedDoc]:
    techs = [_fix_text(t) for t in (proj.technologies or [])]
    text = _join_lines(
        [
            proj.name,
            proj.domain,
            proj.period,
            proj.company_name,
            f"Технологии: {', '.join(techs)}" if techs else "",
            proj.description_md,
            proj.long_description_md,
            f"Репозиторий: {proj.repo_url}" if proj.repo_url else "",
            f"Демо: {proj.demo_url}" if proj.demo_url else "",
        ]
    )
    if not text:
        return []
    meta = {
        "name": _fix_text(proj.name),
        "slug": proj.slug,
        "domain": proj.domain,
        "technologies": techs,
        "company_name": proj.company_name,
        "repo_url": proj.repo_url,
        "demo_url": proj.demo_url,
        "featured": proj.featured,
    }
    return chunk_doc("project", proj.id, text, meta, split_text)


def _technology_docs(
    tech: TechnologyExport, projects_using: list[ProjectExport]
) -> Iterable[NormalizedDoc]:
    proj_names = [_fix_text(p.name) for p in projects_using]
    text = _join_lines(
        [
            tech.name,
            f"Категория: {tech.category}" if tech.category else "",
            f"Используется в: {', '.join(proj_names)}" if proj_names else "",
        ]
    )
    if not text:
        return []
    meta = {
        "name": _fix_text(tech.name),
        "slug": tech.slug,
        "category": tech.category,
        "project_ids": [p.id for p in projects_using],
        "project_names": proj_names,
    }
    return chunk_doc("technology", tech.id, text, meta, split_text)


def _publication_docs(pub: PublicationExport) -> Iterable[NormalizedDoc]:
    text = _join_lines(
        [
            pub.title,
            str(pub.year),
            pub.source,
            pub.description_md,
            pub.url,
        ]
    )
    if not text:
        return []
    meta = {
        "title": _fix_text(pub.title),
        "year": pub.year,
        "source": pub.source,
        "url": pub.url,
        "badge": getattr(pub, "badge", None),
    }
    return chunk_doc("publication", pub.id, text, meta, split_text)


def _focus_area_docs(fa: FocusAreaExport) -> Iterable[NormalizedDoc]:
    bullets = [_fix_text(b.text) for b in fa.bullets]
    text = _join_lines(
        [
            fa.title,
            "Primary" if fa.is_primary else "",
            "\n".join(bullets) if bullets else "",
        ]
    )
    if not text:
        return []
    meta = {
        "title": _fix_text(fa.title),
        "is_primary": fa.is_primary,
        "bullet_count": len(bullets),
    }
    return chunk_doc("focus_area", fa.id, text, meta, split_text)


def _work_approach_docs(wa: WorkApproachExport) -> Iterable[NormalizedDoc]:
    bullets = [_fix_text(b.text) for b in wa.bullets]
    text = _join_lines(
        [
            wa.title,
            "\n".join(bullets) if bullets else "",
        ]
    )
    if not text:
        return []
    meta = {
        "title": _fix_text(wa.title),
        "icon": getattr(wa, "icon", None),
        "bullet_count": len(bullets),
    }
    return chunk_doc("work_approach", wa.id, text, meta, split_text)


def _tech_focus_docs(tf: TechFocusExport) -> Iterable[NormalizedDoc]:
    tags = [_fix_text(t.name) for t in getattr(tf, "tags", [])]
    text = _join_lines(
        [
            tf.label,
            tf.description,
            "\n".join(tags) if tags else "",
        ]
    )
    if not text:
        return []
    meta = {
        "label": _fix_text(tf.label),
        "tags": tags,
    }
    return chunk_doc("tech_focus", tf.id, text, meta, split_text)


def _stat_docs(stat: StatExport) -> Iterable[NormalizedDoc]:
    text = _join_lines(
        [
            stat.label,
            stat.value,
            stat.hint,
            stat.group_name,
        ]
    )
    if not text:
        return []
    meta = {
        "label": _fix_text(stat.label),
        "key": stat.key,
        "group_name": stat.group_name,
    }
    return chunk_doc("stat", stat.id, text, meta, split_text)


def _contact_docs(contact: ContactExport) -> Iterable[NormalizedDoc]:
    text = _join_lines(
        [
            contact.kind,
            contact.label,
            contact.value,
            contact.url,
            "Primary" if contact.is_primary else "",
        ]
    )
    if not text:
        return []
    meta = {
        "kind": contact.kind,
        "label": contact.label,
        "url": contact.url,
        "is_primary": contact.is_primary,
    }
    return chunk_doc("contact", contact.id, text, meta, split_text)


def _catalog_docs(
    payload: ExportPayload,
    projects_by_tech: dict[str, list[ProjectExport]],
    tech_label_by_key: dict[str, str],
) -> Iterable[NormalizedDoc]:
    # --- Catalog: all technologies with per-project usage count ---
    known_keys: set[str] = set()
    entries: list[tuple[str, int]] = []

    for tech in payload.technologies:
        name = _fix_text(tech.name)
        if not name:
            continue
        key = name.casefold()
        known_keys.add(key)
        if tech.slug:
            known_keys.add(_fix_text(tech.slug).casefold())
        usage = projects_by_tech.get(key, [])
        if not usage and tech.slug:
            usage = projects_by_tech.get(_fix_text(tech.slug).casefold(), [])
        entries.append((name, len(usage)))

    for key, projs in projects_by_tech.items():
        if key in known_keys:
            continue
        label = tech_label_by_key.get(key) or key
        label = _fix_text(label)
        if label:
            entries.append((label, len(projs)))

    entries = [e for e in entries if e[0] and e[1] >= 0]
    entries.sort(key=lambda x: (-x[1], x[0].casefold()))

    lines = ["Сводка технологий (всего):"]
    counts: dict[str, int] = {}
    for name, cnt in entries:
        if cnt <= 0:
            continue
        lines.append(f"- {name} — в {cnt} проектах")
        counts[name] = cnt
    text = "\n".join(lines)

    meta = {
        "catalog_kind": "technologies_all",
        "technology_names": list(counts.keys()),
        "technology_counts": counts,
    }
    yield from chunk_doc("catalog", "tech:all", text, meta, split_text)

    # --- Catalog: technologies by company (featured projects) ---
    projects_by_company: dict[str, list[ProjectExport]] = defaultdict(list)
    company_label_by_key: dict[str, str] = {}
    for proj in payload.projects:
        company_label = _fix_text(proj.company_name)
        if not company_label:
            continue
        ckey = company_label.casefold()
        projects_by_company[ckey].append(proj)
        company_label_by_key.setdefault(ckey, company_label)

    for ckey, projs in projects_by_company.items():
        tech_counter: dict[str, int] = {}
        for proj in projs:
            for t in proj.technologies or []:
                t_label = _fix_text(t)
                if not t_label:
                    continue
                tech_counter[t_label] = tech_counter.get(t_label, 0) + 1
        if not tech_counter:
            continue

        ordered = sorted(tech_counter.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
        company_label = company_label_by_key.get(ckey) or ckey
        lines = [f"Сводка технологий по проектам компании: {company_label}"]
        for name, cnt in ordered:
            lines.append(f"- {name} — в {cnt} проектах")
        text = "\n".join(lines)

        meta = {
            "catalog_kind": "technologies_by_company",
            "company_name": company_label,
            "technology_names": [name for name, _ in ordered],
            "technology_counts": dict(tech_counter),
        }
        yield from chunk_doc("catalog", f"tech:company:{_stable_id(ckey)}", text, meta, split_text)


def normalize_export(payload: ExportPayload) -> Iterable[NormalizedDoc]:
    if payload.profile:
        yield from _profile_docs(payload.profile)

    for exp in payload.experiences:
        yield from _experience_docs(exp)
        for proj in exp.projects:
            yield from _experience_project_docs(exp, proj)

    tech_label_by_key: dict[str, str] = {}
    projects_by_tech: dict[str, list[ProjectExport]] = defaultdict(list)
    for proj in payload.projects:
        for tech in proj.technologies or []:
            label = _fix_text(tech)
            if not label:
                continue
            key = label.casefold()
            tech_label_by_key.setdefault(key, label)
            projects_by_tech[key].append(proj)
        yield from _project_docs(proj)

    for tech in payload.technologies:
        usage = projects_by_tech.get(tech.name.casefold(), [])
        if not usage and tech.slug:
            usage = projects_by_tech.get(tech.slug.casefold(), [])
        yield from _technology_docs(tech, usage)

    for pub in payload.publications:
        yield from _publication_docs(pub)

    for fa in payload.focus_areas:
        yield from _focus_area_docs(fa)

    for wa in payload.work_approaches:
        yield from _work_approach_docs(wa)

    for tf in payload.tech_focus:
        yield from _tech_focus_docs(tf)

    for stat in payload.stats:
        yield from _stat_docs(stat)

    for contact in payload.contacts:
        yield from _contact_docs(contact)

    yield from _catalog_docs(payload, projects_by_tech, tech_label_by_key)
