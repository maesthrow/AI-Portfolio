"""
Graph Builder - построение графа знаний из ExportPayload.

Создаёт узлы и рёбра из данных портфолио.
Также заполняет EntityRegistry для поиска сущностей.
"""
from __future__ import annotations

import logging
import re
from typing import List

from ..schemas.export import ExportPayload
from ..rag.entities import get_entity_registry, reset_entity_registry
from ..rag.search_types import EntityType
from .schema import NodeType, EdgeType, GraphNode, GraphEdge
from .store import GraphStore, get_graph_store, reset_graph_store

logger = logging.getLogger(__name__)


def _make_node_id(node_type: NodeType, ref: str | int) -> str:
    """Создать ID узла."""
    return f"{node_type.value}:{ref}"


def _extract_achievements(text: str | None) -> List[str]:
    """
    Извлечь достижения из markdown-текста.

    Парсит bullet points (-, *, •) и обычные строки.
    """
    if not text:
        return []

    lines = text.strip().split("\n")
    achievements = []

    for line in lines:
        line = line.strip()
        # Убираем маркеры списка
        if line.startswith(("-", "*", "•")):
            line = re.sub(r"^[-*•]\s*", "", line).strip()
        # Убираем нумерацию
        line = re.sub(r"^\d+\.\s*", "", line).strip()

        if line and len(line) > 10:  # Минимальная длина достижения
            achievements.append(line)

    return achievements


def _generate_aliases(name: str) -> List[str]:
    """Генерировать алиасы для названия."""
    aliases = []

    # Транслитерация и варианты
    name_lower = name.lower()

    # Без пробелов и дефисов
    aliases.append(name_lower.replace(" ", "").replace("-", ""))
    aliases.append(name_lower.replace(" ", "-"))
    aliases.append(name_lower.replace("-", " "))

    # Только первое слово (для длинных названий)
    words = name.split()
    if len(words) > 1:
        aliases.append(words[0].lower())

    # Убираем пустые и дубли
    return list(set(a for a in aliases if a and a != name_lower))


def build_graph_from_export(payload: ExportPayload) -> GraphStore:
    """
    Построить граф знаний из ExportPayload.

    Создаёт узлы и рёбра для всех сущностей портфолио.
    Также заполняет EntityRegistry для поиска.

    Args:
        payload: Данные портфолио из content-api

    Returns:
        GraphStore с построенным графом
    """
    # Сброс хранилищ
    store = reset_graph_store()
    registry = reset_entity_registry()

    person_id: str | None = None

    # === 1. Profile -> Person node ===
    if payload.profile:
        p = payload.profile
        person_id = _make_node_id(NodeType.PERSON, p.id)

        store.add_node(GraphNode(
            id=person_id,
            type=NodeType.PERSON,
            name=p.full_name,
            slug="dmitry",
            data={
                "title": p.title,
                "subtitle": p.subtitle,
                "current_position": p.current_position,
                "hero_headline": p.hero_headline,
                "hero_description": p.hero_description,
                "summary_md": p.summary_md,
            }
        ))

        registry.register(
            EntityType.PERSON,
            "dmitry",
            p.full_name,
            [p.title or "", "разработчик", "developer", "дмитрий"]
        )

    # === 2. Technologies ===
    tech_id_by_name: dict[str, str] = {}

    for tech in payload.technologies:
        tid = _make_node_id(NodeType.TECHNOLOGY, tech.id)
        tech_id_by_name[tech.name.lower()] = tid

        store.add_node(GraphNode(
            id=tid,
            type=NodeType.TECHNOLOGY,
            name=tech.name,
            slug=tech.slug,
            data={"category": tech.category}
        ))

        registry.register(
            EntityType.TECHNOLOGY,
            tech.slug,
            tech.name,
            _generate_aliases(tech.name)
        )

        # Person -> Technology (KNOWS)
        if person_id:
            store.add_edge(GraphEdge(person_id, tid, EdgeType.KNOWS))

    # === 3. Companies from Experience ===
    company_id_by_slug: dict[str, str] = {}

    for exp in payload.experiences:
        cid = _make_node_id(NodeType.COMPANY, exp.id)
        company_id_by_slug[exp.company_slug] = cid

        company_name = exp.company_name or exp.role

        store.add_node(GraphNode(
            id=cid,
            type=NodeType.COMPANY,
            name=company_name,
            slug=exp.company_slug,
            data={
                "role": exp.role,
                "start_date": str(exp.start_date) if exp.start_date else None,
                "end_date": str(exp.end_date) if exp.end_date else None,
                "is_current": exp.is_current,
                "kind": exp.kind,
                "company_summary_md": exp.company_summary_md,
                "company_role_md": exp.company_role_md,
            }
        ))

        registry.register(
            EntityType.COMPANY,
            exp.company_slug,
            company_name,
            [exp.role] + _generate_aliases(company_name)
        )

        # Person -> Company (WORKS_AT / WORKED_AT)
        if person_id:
            edge_type = EdgeType.WORKS_AT if exp.is_current else EdgeType.WORKED_AT
            store.add_edge(GraphEdge(
                person_id, cid, edge_type,
                {"role": exp.role, "is_current": exp.is_current}
            ))

        # === Experience Projects -> Project + Achievement nodes ===
        for proj in exp.projects:
            project_slug = proj.slug or f"exp-{proj.id}"
            pid = _make_node_id(NodeType.PROJECT, f"exp:{proj.id}")

            store.add_node(GraphNode(
                id=pid,
                type=NodeType.PROJECT,
                name=proj.name,
                slug=project_slug,
                data={
                    "period": proj.period,
                    "description_md": proj.description_md,
                    "achievements_md": proj.achievements_md,
                    "experience_id": exp.id,
                    "company_slug": exp.company_slug,
                    "company_name": company_name,
                }
            ))

            registry.register(
                EntityType.PROJECT,
                project_slug,
                proj.name,
                _generate_aliases(proj.name)
            )

            # Person -> Project (CREATED)
            if person_id:
                store.add_edge(GraphEdge(person_id, pid, EdgeType.CREATED))

            # Project -> Company (BELONGS_TO)
            store.add_edge(GraphEdge(pid, cid, EdgeType.BELONGS_TO))

            # Parse achievements
            for idx, ach_text in enumerate(_extract_achievements(proj.achievements_md)):
                aid = _make_node_id(NodeType.ACHIEVEMENT, f"{proj.id}:{idx}")

                store.add_node(GraphNode(
                    id=aid,
                    type=NodeType.ACHIEVEMENT,
                    name=ach_text[:100],  # Короткое имя
                    slug=f"ach-{proj.id}-{idx}",
                    data={
                        "text": ach_text,
                        "project_slug": project_slug,
                        "project_name": proj.name,
                        "company_slug": exp.company_slug,
                        "company_name": company_name,
                    }
                ))

                # Person -> Achievement (ACHIEVED)
                if person_id:
                    store.add_edge(GraphEdge(person_id, aid, EdgeType.ACHIEVED))

                # Achievement -> Project (BELONGS_TO)
                store.add_edge(GraphEdge(aid, pid, EdgeType.BELONGS_TO))

    # === 4. Standalone Projects ===
    for proj in payload.projects:
        pid = _make_node_id(NodeType.PROJECT, proj.id)

        store.add_node(GraphNode(
            id=pid,
            type=NodeType.PROJECT,
            name=proj.name,
            slug=proj.slug,
            data={
                "domain": proj.domain,
                "period": proj.period,
                "description_md": proj.description_md,
                "long_description_md": proj.long_description_md,
                "repo_url": proj.repo_url,
                "demo_url": proj.demo_url,
                "featured": proj.featured,
                "company_name": proj.company_name,
                "technologies": proj.technologies,
            }
        ))

        registry.register(
            EntityType.PROJECT,
            proj.slug,
            proj.name,
            _generate_aliases(proj.name)
        )

        # Person -> Project (CREATED)
        if person_id:
            store.add_edge(GraphEdge(person_id, pid, EdgeType.CREATED))

        # Project -> Technology (USES)
        for tech_name in (proj.technologies or []):
            tid = tech_id_by_name.get(tech_name.lower())
            if tid:
                store.add_edge(GraphEdge(pid, tid, EdgeType.USES))

    # === 5. Contacts ===
    for contact in payload.contacts:
        cid = _make_node_id(NodeType.CONTACT, contact.id)

        store.add_node(GraphNode(
            id=cid,
            type=NodeType.CONTACT,
            name=contact.label,
            slug=contact.kind,
            data={
                "kind": contact.kind,
                "value": contact.value,
                "url": contact.url,
                "is_primary": contact.is_primary,
            }
        ))

        # Person -> Contact (HAS_CONTACT)
        if person_id:
            store.add_edge(GraphEdge(person_id, cid, EdgeType.HAS_CONTACT))

    logger.info("Graph built: %s, EntityRegistry: %s",
                store.stats(), registry.stats())

    return store
