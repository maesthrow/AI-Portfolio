from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re
from typing import Any

from ..deps import vectorstore
from .utils import md_get_list

_KEY_CLEAN_RE = re.compile(r"[^\w]+", re.UNICODE)
_LEGAL_FORMS = {
    "ооо",
    "ао",
    "зао",
    "оао",
    "ип",
    "llc",
    "inc",
    "ltd",
    "gmbh",
    "plc",
}


def normalize_key(value: str | None) -> str:
    txt = (value or "").casefold()
    txt = _KEY_CLEAN_RE.sub(" ", txt)
    return " ".join(txt.split()).strip()


def _compact(value: str) -> str:
    return value.replace(" ", "")


def _strip_legal_forms(value: str) -> str:
    parts = [p for p in value.split() if p and p not in _LEGAL_FORMS]
    return " ".join(parts).strip()


def _aliases_for_name(name: str | None, *, kind: str) -> set[str]:
    base = normalize_key(name)
    if not base:
        return set()

    out: set[str] = {base, _compact(base)}

    if kind == "company":
        stripped = _strip_legal_forms(base)
        if stripped and stripped != base:
            out.add(stripped)
            out.add(_compact(stripped))

    return {a for a in out if len(a) >= 2}


@dataclass(frozen=True)
class EntityCandidate:
    kind: str  # project|company|technology
    name: str
    slug: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> str:
        return normalize_key(self.name) or (normalize_key(self.slug) if self.slug else "")

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.slug or self.key}"


@dataclass(frozen=True)
class EntityMatch:
    kind: str
    name: str
    slug: str | None = None
    matched_alias: str | None = None
    score: float = 1.0

    @property
    def key(self) -> str:
        return normalize_key(self.name) or (normalize_key(self.slug) if self.slug else "")

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.slug or self.key}"


@dataclass
class EntityRegistry:
    # alias -> candidate
    projects: dict[str, EntityCandidate] = field(default_factory=dict)
    companies: dict[str, EntityCandidate] = field(default_factory=dict)
    technologies: dict[str, EntityCandidate] = field(default_factory=dict)


def _add_aliases(bucket: dict[str, EntityCandidate], candidate: EntityCandidate, aliases: set[str]) -> None:
    for a in aliases:
        # Prefer longer aliases to reduce ambiguity in match selection.
        prev = bucket.get(a)
        if prev is None or len(candidate.name) > len(prev.name):
            bucket[a] = candidate


def _collect_candidates(metas: list[dict[str, Any]]) -> EntityRegistry:
    reg = EntityRegistry()

    for md in metas:
        t = md.get("type")

        if t in {"project", "experience_project", "item"}:
            proj_slug = md.get("project_slug") or md.get("slug")
            proj_name = md.get("project_name") or md.get("name")
            if isinstance(proj_name, str) and proj_name.strip():
                cand = EntityCandidate(kind="project", name=str(proj_name).strip(), slug=str(proj_slug).strip() if proj_slug else None)
                _add_aliases(reg.projects, cand, _aliases_for_name(cand.slug, kind="project") | _aliases_for_name(cand.name, kind="project"))

        if t in {"experience", "experience_project", "project", "item"}:
            comp_slug = md.get("company_slug")
            comp_name = md.get("company_name")
            if isinstance(comp_name, str) and comp_name.strip():
                cand = EntityCandidate(kind="company", name=str(comp_name).strip(), slug=str(comp_slug).strip() if comp_slug else None)
                _add_aliases(reg.companies, cand, _aliases_for_name(cand.slug, kind="company") | _aliases_for_name(cand.name, kind="company"))

        if t == "technology":
            tech_slug = md.get("slug")
            tech_name = md.get("name")
            if isinstance(tech_name, str) and tech_name.strip():
                cand = EntityCandidate(kind="technology", name=str(tech_name).strip(), slug=str(tech_slug).strip() if tech_slug else None)
                _add_aliases(reg.technologies, cand, _aliases_for_name(cand.slug, kind="technology") | _aliases_for_name(cand.name, kind="technology"))

        if t == "project":
            for tech in md_get_list(md, "technologies"):
                if not tech:
                    continue
                cand = EntityCandidate(kind="technology", name=tech, slug=None)
                _add_aliases(reg.technologies, cand, _aliases_for_name(cand.name, kind="technology"))

    return reg


def _load_all_metadatas(vs) -> list[dict[str, Any]]:
    coll = getattr(vs, "_collection", None)
    if coll is None or not hasattr(coll, "get"):
        return []

    include = ["metadatas"]
    try:
        data = coll.get(include=include, limit=20_000)
    except TypeError:
        try:
            data = coll.get(include=include)
        except Exception:
            return []
    except Exception:
        return []

    metas = data.get("metadatas") if isinstance(data, dict) else None
    if not isinstance(metas, list):
        return []
    return [m for m in metas if isinstance(m, dict)]


@lru_cache
def get_entity_registry(collection: str) -> EntityRegistry:
    vs = vectorstore(collection)
    metas = _load_all_metadatas(vs)
    return _collect_candidates(metas)


def clear_entity_registry_cache() -> None:
    """
    Вызывать после реиндекса/очистки коллекции, чтобы registry не оставался "старым".
    """
    try:
        get_entity_registry.cache_clear()
    except Exception:
        pass


def extract_entities(question: str, registry: EntityRegistry) -> list[EntityMatch]:
    q_norm = normalize_key(question)
    if not q_norm:
        return []
    q_compact = _compact(q_norm)
    tokens = set(q_norm.split())

    def _match(bucket: dict[str, EntityCandidate]) -> list[tuple[int, EntityCandidate, str]]:
        matches: list[tuple[int, EntityCandidate, str]] = []
        # Longest aliases first: helps pick the most specific match.
        for alias, cand in sorted(bucket.items(), key=lambda kv: len(kv[0]), reverse=True):
            if not alias:
                continue
            if len(alias) <= 3 and alias not in tokens:
                continue
            if alias in q_norm or alias in q_compact:
                matches.append((len(alias), cand, alias))
        return matches

    def _pick(matches: list[tuple[int, EntityCandidate, str]], *, limit: int) -> list[EntityMatch]:
        if not matches:
            return []
        # Dedup by candidate id, keep best alias (longest).
        best: dict[str, tuple[int, EntityCandidate, str]] = {}
        for ln, cand, alias in matches:
            prev = best.get(cand.id)
            if prev is None or ln > prev[0]:
                best[cand.id] = (ln, cand, alias)
        ordered = sorted(best.values(), key=lambda x: (x[0], len(x[1].name)), reverse=True)
        out: list[EntityMatch] = []
        for ln, cand, alias in ordered[: max(1, limit)]:
            score = min(1.0, 0.55 + 0.015 * ln)
            out.append(EntityMatch(kind=cand.kind, name=cand.name, slug=cand.slug, matched_alias=alias, score=score))
        return out

    projects = _pick(_match(registry.projects), limit=2)
    companies = _pick(_match(registry.companies), limit=2)
    technologies = _pick(_match(registry.technologies), limit=3)

    return projects + companies + technologies
