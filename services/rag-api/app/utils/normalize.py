# services/rag-api/app/utils/normalize.py
import hashlib, json
from typing import Iterable, Tuple, Dict, Any
from ..schemas.ingest_schema import ExportPayload


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


def normalize_export(payload: ExportPayload) -> Iterable[Tuple[str, str, Dict[str, Any]]]:
    # projects
    for p in payload.projects:
        lines = [f"Project: {p.name}"]
        if p.company_name: lines.append(f"Company: {p.company_name}")
        if p.period: lines.append(f"Period: {p.period}")
        if p.technologies: lines.append("Technologies: " + ", ".join(p.technologies))
        if p.description: lines.append(p.description.strip())
        text = "\n".join(lines)
        meta = {
            "name": p.name, "company_id": p.company_id, "company_name": p.company_name,
            "period": p.period, "period_start": p.period_start, "period_end": p.period_end,
            "technologies": p.technologies, "url": p.url,
        }
        yield _mk("project", p.id, text, meta)

    # technologies
    for t in payload.technologies:
        desc = f"Technology: {t.name}"
        if t.aliases: desc += "\nAliases: " + ", ".join(t.aliases)
        yield _mk("technology", t.id, desc, {"name": t.name, "aliases": t.aliases, "url": t.url})

    # companies
    for c in payload.companies:
        text = f"Company: {c.name}"
        if c.description: text += "\n" + c.description.strip()
        if c.website: text += f"\nWebsite: {c.website}"
        yield _mk("company", c.id, text, {"name": c.name, "website": c.website})

    # achievements
    for a in payload.achievements:
        text = f"Achievement: {a.title}"
        if a.description: text += "\n" + a.description.strip()
        if a.links: text += "\nLinks: " + ", ".join(a.links)
        yield _mk("achievement", a.id, text, {"title": a.title, "project_id": a.project_id, "links": a.links})

    # documents
    for d in payload.documents:
        lines = [f"Document: {d.title}", f"URL: {d.url}"]
        if d.doc_type: lines.append(f"Type: {d.doc_type}")
        if d.summary: lines.append(d.summary.strip())
        text = "\n".join(lines)
        meta = {"title": d.title, "project_id": d.project_id, "company_id": d.company_id,
                "doc_type": d.doc_type, "url": d.url, "meta": d.meta or {}}
        yield _mk("document", d.id, text, meta)
