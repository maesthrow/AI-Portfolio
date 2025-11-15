from collections import Counter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .deps import vectorstore, reranker, chat_llm, settings
from .rag.prompting import make_system_prompt, build_messages_for_answer, build_messages_when_empty, classify_intent
from .rag.retrieval import HybridRetriever, DenseRetriever
from .rag.rank import rerank
from .rag.evidence import select_evidence, pack_context
from .rag.utils import md_get_list, md_get_dict

router = APIRouter(tags=["ask"])


class AskReq(BaseModel):
    question: str
    k: int = 8
    collection: str | None = None
    system_prompt: str | None = None


def _aggregate_tech_names(docs) -> list[str]:
    """Агрегация технологий из документов (catalog/technology/project)."""
    counts = Counter()
    saw_catalog = any((getattr(d, "metadata", None) or {}).get("type") == "catalog" for d in docs)
    if saw_catalog:
        for d in docs:
            md = (getattr(d, "metadata", None) or {})
            if md.get("type") != "catalog":
                continue
            names = md_get_list(md, "technology_names")
            cm = md_get_dict(md, "technology_counts")
            if cm:
                for n in names:
                    counts[n] += int(cm.get(n, 1))
            else:
                for n in names:
                    counts[n] += 1
    else:
        for d in docs:
            md = (getattr(d, "metadata", None) or {})
            ty = md.get("type")
            if ty == "technology":
                name = md.get("name") or md.get("technology_name")
                if isinstance(name, str) and name.strip():
                    counts[name.strip()] += 1
            elif ty == "project":
                names = md_get_list(md, "technology_names") or md_get_list(md, "technologies")
                for n in names:
                    counts[n] += 1
    ordered = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0].casefold()))
    return [name for name, _ in ordered]


@router.post("/ask")
def ask(req: AskReq):
    cfg = settings()
    coll = req.collection or cfg.chroma_collection
    vs = vectorstore(coll)
    llm = chat_llm()
    rr = reranker()

    sys_prompt = make_system_prompt(req.system_prompt)

    # 0) Интент вопроса
    intent = classify_intent(llm, req.question)  # 'IDENTITY' | 'TECH_LIST' | 'GENERAL'

    # 1) Ветка: идентификация (короткий ответ, минимум источников)
    if intent == "IDENTITY":
        try:
            hybrid = HybridRetriever(vs, collection=coll)
            candidates_all = hybrid.retrieve(req.question, k_dense=max(req.k * 4, 40), k_bm=max(req.k * 4, 40), k_final=max(req.k * 3, req.k))
        except Exception as e:
            candidates_all = []
        if not candidates_all:
            out = llm.invoke(build_messages_when_empty(sys_prompt, req.question, style_hint="ULTRASHORT"))
            return {"answer": out.content, "sources": [], "found": 0, "collection": coll, "model": cfg.chat_model}

        scored = rerank(rr, req.question, candidates_all)
        base = select_evidence(scored, req.question, k=req.k, min_k=3)  # мало и ёмко
        context = pack_context(base, token_budget=200)  # маленький бюджет = короткий ответ

        out = llm.invoke(build_messages_for_answer(sys_prompt, req.question, context, style_hint="ULTRASHORT"))

        sources = []
        for sd in base:
            md = sd.doc.metadata or {}
            sources.append({
                "id": md.get("ref_id") or md.get("id") or md.get("source"),
                "type": md.get("type"),
                "score": float(sd.score),
                "title": md.get("name") or md.get("title"),
                "url": md.get("repo_url") or md.get("demo_url"),
                "kind": md.get("kind"),
                "repo_url": None,
                "demo_url": None,
            })

        return {
            "answer": out.content,
            "sources": sources,
            "found": len(candidates_all),
            "collection": coll,
            "model": cfg.chat_model
        }

    # 2) Ветка: перечисление технологий (агрегация + компактный список)
    if intent == "TECH_LIST":
        k_dense = max(req.k * 10, 80)
        dense_docs = DenseRetriever(vs, where={"type": {"$in": ["catalog", "technology", "project"]}}).retrieve(
            req.question, k_dense
        )
        if not dense_docs:
            out = llm.invoke(build_messages_when_empty(sys_prompt, req.question, style_hint="LIST"))
            return {"answer": out.content, "sources": [], "found": 0, "collection": coll, "model": cfg.chat_model}

        scored = rerank(rr, req.question, dense_docs)
        base = select_evidence(scored, req.question, k=req.k, min_k=max(req.k, 8))

        tech_names = _aggregate_tech_names([sd.doc for sd in scored])[:40]
        context = "Мои ключевые технологии: " + ", ".join(tech_names) + "."
        # Поддержка 1–2 фрагментами (по желанию):
        if scored:
            support = "\n\n".join([sd.doc.page_content for sd in scored[:2]])
            context += f"\n\nПримеры:\n{support}"

        out = llm.invoke(build_messages_for_answer(sys_prompt, req.question, context, style_hint="LIST"))

        sources = []
        for sd in base:
            md = sd.doc.metadata or {}
            sources.append({
                "id": md.get("ref_id") or md.get("id") or md.get("source"),
                "type": md.get("type"),
                "score": float(sd.score),
                "title": md.get("name") or md.get("title"),
                "url": md.get("repo_url") or md.get("demo_url"),
                "kind": md.get("kind"),
                "repo_url": None,
                "demo_url": None,
            })

        return {
            "answer": out.content,
            "sources": sources,
            "found": len(scored),
            "collection": coll,
            "model": cfg.chat_model
        }

    # 3) Ветка: общий вопрос
    try:
        hybrid = HybridRetriever(vs, collection=coll)
        candidates_all = hybrid.retrieve(req.question, k_dense=max(req.k * 4, 40), k_bm=max(req.k * 4, 40), k_final=max(req.k * 3, req.k))
    except Exception as e:
        raise HTTPException(500, f"Retrieval failed: {e}")

    if not candidates_all:
        out = llm.invoke(build_messages_when_empty(sys_prompt, req.question))
        return {"answer": out.content, "sources": [], "found": 0, "collection": coll, "model": cfg.chat_model}

    scored = rerank(rr, req.question, candidates_all)
    base = select_evidence(scored, req.question, k=req.k, min_k=max(req.k, 8))
    context = pack_context(base, token_budget=900)

    out = llm.invoke(build_messages_for_answer(sys_prompt, req.question, context))

    sources = []
    for sd in base:
        md = sd.doc.metadata or {}
        sources.append({
            "id": md.get("ref_id") or md.get("id") or md.get("source"),
            "type": md.get("type"),
            "score": float(sd.score),
            "title": md.get("name") or md.get("title"),
            "url": md.get("repo_url") or md.get("demo_url"),
            "kind": md.get("kind"),
            "repo_url": None,
            "demo_url": None,
        })

    return {
        "answer": out.content,
        "sources": sources,
        "found": len(candidates_all),
        "collection": coll,
        "model": cfg.chat_model
    }
