from __future__ import annotations
from langchain.tools import tool
from ..deps import vectorstore, settings
from ..rag.core import portfolio_rag_answer
from ..rag.search import portfolio_search
import logging
import re
from dataclasses import asdict
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_SENT_SPLITTER = re.compile(r"(?<=[\.\!\?])\s+")


def _snippet(text: str, *, max_chars: int = 260) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    sents = [s.strip() for s in _SENT_SPLITTER.split(raw) if s and s.strip()]
    if not sents:
        return raw[:max_chars].strip()
    out = " ".join(sents[:2]).strip()
    if len(out) > max_chars:
        out = out[: max_chars - 1].rstrip() + "…"
    return out


def _extract_after_label(text: str, label: str) -> str:
    if not text:
        return ""
    low = text.casefold()
    lab = label.casefold()
    idx = low.rfind(lab)
    if idx < 0:
        return text.strip()
    return text[idx + len(label) :].strip(" .:\n\t")


def _norm_key(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").casefold()).strip()


@tool("portfolio_rag_tool")
def portfolio_rag_tool(question: str) -> dict:
    """
    Получить ответ из портфолио разработчика Дмитрия Каргина через RAG.
    Всегда использовать для вопросов о проектах, компаниях, технологиях, опыте, достижениях и документах.
    """
    logger.info("portfolio_rag_tool called question=%r", question)
    try:
        data = portfolio_rag_answer(question=question)
        return {"ok": True, **data}
    except Exception as exc:
        logger.exception("portfolio_rag_tool failed")
        return {"ok": False, "error": str(exc), "question": question}


@tool("portfolio_search_tool")
def portfolio_search_tool(question: str) -> dict[str, Any]:
    """
    Возвращает структурированные факты из портфолио разработчика Дмитрия Каргина:
    intent, entities, items (в т.ч. achievements), evidence snippets, sources, confidence.

    Используется агентом как "источник фактов" для финального ответа без пересказа пересказа.
    """
    logger.info("portfolio_search_tool called question=%r", question)
    try:
        cfg = settings()
        res = portfolio_search(question=question, k=cfg.rag_list_max_items, collection=cfg.chroma_collection)
    except Exception as exc:
        logger.exception("portfolio_search_tool failed")
        return {"ok": False, "error": str(exc), "question": question}

    plan = res.plan

    entities = [
        {
            "kind": e.kind,
            "name": e.name,
            "slug": e.slug,
            "matched_alias": e.matched_alias,
            "score": float(e.score),
        }
        for e in (plan.entities or [])
    ]

    # items: атомарные факты (достижения/контакты/теги/буллеты/статы)
    items: list[dict[str, Any]] = []
    achievements_raw: dict[str, list[dict[str, Any]]] = {}
    max_items = max(4, int(getattr(cfg, "rag_list_max_items", 16) or 16))

    for sd in res.evidence:
        md = sd.doc.metadata or {}
        if md.get("type") != "item":
            continue
        item_kind = md.get("item_kind")
        item_text = (sd.doc.page_content or "").strip()
        if not item_text:
            continue
        item = {
            "kind": item_kind,
            "text": item_text,
            "score": float(sd.score),
            "order_index": int(md.get("order_index") or 0),
            "project_name": md.get("project_name"),
            "project_slug": md.get("project_slug"),
            "company_name": md.get("company_name"),
            "company_slug": md.get("company_slug"),
            "parent_doc_id": md.get("parent_doc_id"),
            "source_field": md.get("source_field"),
        }
        items.append(item)

        if item_kind == "achievement":
            proj = (md.get("project_name") or md.get("project_slug") or "").strip()
            comp = (md.get("company_name") or md.get("company_slug") or "").strip()
            group = proj or comp or "Другое"
            bullet = _extract_after_label(item_text, "Достижение:")
            if bullet:
                achievements_raw.setdefault(group, []).append(
                    {
                        "text": bullet,
                        "order_index": int(md.get("order_index") or 0),
                        "score": float(sd.score),
                    }
                )

        if len(items) >= max_items:
            break

    # Стабилизируем порядок items (особенно для достижений): order_index -> score.
    def _item_sort_key(it: dict[str, Any]) -> tuple:
        kind = str(it.get("kind") or "")
        order = int(it.get("order_index") or 0)
        order_key = order if order > 0 else 10_000
        return (kind, it.get("project_name") or "", it.get("company_name") or "", order_key, -float(it.get("score") or 0.0))

    items.sort(key=_item_sort_key)

    achievements: dict[str, list[str]] = {}
    for group, rows in achievements_raw.items():
        rows_sorted = sorted(
            rows,
            key=lambda r: (int(r.get("order_index") or 0) if int(r.get("order_index") or 0) > 0 else 10_000, -float(r.get("score") or 0.0), str(r.get("text") or "").casefold()),
        )
        uniq: list[str] = []
        seen = set()
        for r in rows_sorted:
            txt = str(r.get("text") or "").strip()
            if not txt:
                continue
            k = _norm_key(txt)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(txt)
        if uniq:
            achievements[group] = uniq[:max_items]

    # evidence snippets: короткие выдержки (без full-text), чтобы агент мог отвечать "по фактам"
    snippets: list[dict[str, Any]] = []
    max_snips = 10
    for sd in res.evidence:
        md = sd.doc.metadata or {}
        t = md.get("type")
        if t == "item":
            continue
        title = md.get("name") or md.get("title") or md.get("label") or md.get("kind")
        snippets.append(
            {
                "type": t,
                "title": title,
                "score": float(sd.score),
                "snippet": _snippet(sd.doc.page_content or ""),
            }
        )
        if len(snippets) >= max_snips:
            break

    sources = [asdict(s) for s in (res.sources or [])][:12]

    # лёгкий сигнал об неоднозначности: несколько совпавших проектов/компаний
    ambiguity = {
        "projects": [e for e in entities if e["kind"] == "project"],
        "companies": [e for e in entities if e["kind"] == "company"],
    }

    return {
        "question": question,
        "intent": plan.intent.value,
        "entity_policy": plan.entity_policy.value,
        "entities": entities,
        "answer_instructions": plan.answer_instructions,
        "allowed_types": sorted(list(plan.allowed_types)) if plan.allowed_types else None,
        "item_kinds": sorted(list(plan.item_kinds)) if plan.item_kinds else [],
        "confidence": float(res.confidence),
        "found": int(res.found),
        "collection": res.collection,
        "items": items,
        "achievements": achievements,
        "evidence_snippets": snippets,
        "sources": sources,
        "ambiguity": ambiguity,
    }


@tool("list_projects_tool")
def list_projects_tool(limit: int = 10) -> str:
    """
    Кратко перечисляет основные проекты и компании из портфолио разработчика Дмитрия Каргина.
    """
    s = settings()
    vs = vectorstore(s.chroma_collection)

    # Берём несколько документов типа 'project'
    docs = vs.similarity_search("проекты разработчика", k=limit, filter={"type": "project"})
    seen = set()
    lines: list[str] = []
    for d in docs:
        md = d.metadata or {}
        proj = md.get("name") or md.get("title")
        comp = md.get("company_name") or md.get("company")
        key = (proj, comp)
        if key in seen:
            continue
        seen.add(key)
        if proj:
            if comp:
                lines.append(f"- {proj} (компания: {comp})")
            else:
                lines.append(f"- {proj}")

    if not lines:
        return "У меня нет информации о проектах в базе портфолио."

    return "Некоторые проекты Дмитрия Каргина:\n" + "\n".join(lines)
