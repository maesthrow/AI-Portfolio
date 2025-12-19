"""
Graph Query - запросы к графу знаний.

Функции для извлечения структурированных фактов из графа
по различным Intent'ам.
"""
from __future__ import annotations

from typing import Any, Dict, List

from ..rag.search_types import Intent, GraphQueryResult
from .schema import NodeType, EdgeType, GraphNode
from .store import get_graph_store


def _node_to_source(node: GraphNode) -> Dict[str, Any]:
    """Преобразовать узел в формат source."""
    return {
        "id": node.id,
        "type": node.type.value,
        "title": node.name,
        "slug": node.slug,
        **node.data,
    }


def _achievements_query(entity_key: str | None) -> GraphQueryResult:
    """
    Запрос достижений.

    Если entity_key указан, фильтрует по project_slug или company_slug.
    """
    store = get_graph_store()
    achievements = store.get_nodes_by_type(NodeType.ACHIEVEMENT)

    if entity_key:
        key_lower = entity_key.lower()
        filtered = []
        for ach in achievements:
            proj_slug = (ach.data.get("project_slug") or "").lower()
            comp_slug = (ach.data.get("company_slug") or "").lower()
            proj_name = (ach.data.get("project_name") or "").lower()
            comp_name = (ach.data.get("company_name") or "").lower()

            if (key_lower in proj_slug or key_lower in comp_slug or
                key_lower in proj_name or key_lower in comp_name or
                proj_slug in key_lower or comp_slug in key_lower):
                filtered.append(ach)
        achievements = filtered

    items = [
        {
            "text": a.data.get("text", a.name),
            "project": a.data.get("project_name"),
            "company": a.data.get("company_name"),
        }
        for a in achievements
    ]
    sources = [_node_to_source(a) for a in achievements[:10]]

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=sources,
        confidence=0.9 if items else 0.0,
        intent=Intent.ACHIEVEMENTS,
        entity_key=entity_key,
    )


def _current_job_query() -> GraphQueryResult:
    """Запрос текущего места работы."""
    store = get_graph_store()

    # Ищем компании с is_current=True
    companies = store.find_nodes_by_data(NodeType.COMPANY, "is_current", True)

    if not companies:
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.CURRENT_JOB,
        )

    items = [
        {
            "company": c.name,
            "role": c.data.get("role"),
            "start_date": c.data.get("start_date"),
        }
        for c in companies
    ]

    return GraphQueryResult(
        items=items,
        found=True,
        sources=[_node_to_source(c) for c in companies],
        confidence=0.95,
        intent=Intent.CURRENT_JOB,
    )


def _contacts_query() -> GraphQueryResult:
    """Запрос контактной информации."""
    store = get_graph_store()
    contacts = store.get_nodes_by_type(NodeType.CONTACT)

    items = [
        {
            "kind": c.data.get("kind"),
            "label": c.name,
            "value": c.data.get("value"),
            "url": c.data.get("url"),
        }
        for c in contacts
    ]

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=[_node_to_source(c) for c in contacts],
        confidence=0.95 if items else 0.0,
        intent=Intent.CONTACTS,
    )


def _languages_query() -> GraphQueryResult:
    """Запрос языков программирования."""
    store = get_graph_store()
    techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)

    # Фильтруем по категории или известным языкам
    known_languages = {
        "python", "javascript", "typescript", "java", "go", "rust",
        "c++", "c#", "kotlin", "swift", "ruby", "php", "scala",
        "sql", "bash", "shell"
    }
    lang_categories = {"language", "programming", "backend", "frontend"}

    languages = []
    for t in techs:
        category = (t.data.get("category") or "").lower()
        name_lower = t.name.lower()

        if category in lang_categories or name_lower in known_languages:
            languages.append(t)

    # Если не нашли по категориям, возвращаем все технологии
    if not languages:
        languages = techs[:15]

    items = [
        {
            "name": t.name,
            "category": t.data.get("category"),
        }
        for t in languages
    ]

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=[_node_to_source(t) for t in languages[:10]],
        confidence=0.85 if items else 0.0,
        intent=Intent.LANGUAGES,
    )


def _technologies_query(entity_key: str | None) -> GraphQueryResult:
    """Запрос технологий (опционально по проекту)."""
    store = get_graph_store()

    if entity_key:
        # Ищем технологии конкретного проекта
        project = store.get_node_by_slug(entity_key)
        if not project:
            # Пробуем найти по частичному совпадению
            projects = store.get_nodes_by_type(NodeType.PROJECT)
            for p in projects:
                if entity_key.lower() in p.slug.lower() or entity_key.lower() in p.name.lower():
                    project = p
                    break

        if project:
            # Получаем технологии через рёбра USES
            tech_edges = store.get_outgoing_edges(project.id, EdgeType.USES)
            techs = [store.get_node(e.target_id) for e in tech_edges]
            techs = [t for t in techs if t]

            # Также проверяем поле technologies в data
            tech_names = project.data.get("technologies") or []
            for name in tech_names:
                existing = {t.name.lower() for t in techs}
                if name.lower() not in existing:
                    # Ищем технологию по имени
                    for t in store.get_nodes_by_type(NodeType.TECHNOLOGY):
                        if t.name.lower() == name.lower():
                            techs.append(t)
                            break

            items = [{"name": t.name, "category": t.data.get("category")} for t in techs]
            return GraphQueryResult(
                items=items,
                found=len(items) > 0,
                sources=[_node_to_source(t) for t in techs[:10]],
                confidence=0.9 if items else 0.0,
                intent=Intent.TECHNOLOGIES,
                entity_key=entity_key,
            )

    # Все технологии
    techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)
    items = [{"name": t.name, "category": t.data.get("category")} for t in techs]

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=[_node_to_source(t) for t in techs[:10]],
        confidence=0.85 if items else 0.0,
        intent=Intent.TECHNOLOGIES,
    )


def _project_details_query(entity_key: str) -> GraphQueryResult:
    """Запрос деталей конкретного проекта."""
    store = get_graph_store()

    if not entity_key:
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.PROJECT_DETAILS,
        )

    project = store.get_node_by_slug(entity_key)

    if not project:
        # Пробуем найти по частичному совпадению
        projects = store.get_nodes_by_type(NodeType.PROJECT)
        for p in projects:
            if (entity_key.lower() in p.slug.lower() or
                entity_key.lower() in p.name.lower()):
                project = p
                break

    if not project:
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.PROJECT_DETAILS,
            entity_key=entity_key,
        )

    # Получаем связанные технологии
    tech_edges = store.get_outgoing_edges(project.id, EdgeType.USES)
    techs = [store.get_node(e.target_id) for e in tech_edges]
    techs = [t for t in techs if t]

    # Также из data
    tech_list = project.data.get("technologies") or []
    tech_names = [t.name for t in techs] + tech_list

    # Получаем достижения проекта
    achievements = []
    for ach in store.get_nodes_by_type(NodeType.ACHIEVEMENT):
        if ach.data.get("project_slug") == project.slug:
            achievements.append(ach.data.get("text", ach.name))

    item = {
        "name": project.name,
        "slug": project.slug,
        "description": project.data.get("description_md"),
        "long_description": project.data.get("long_description_md"),
        "domain": project.data.get("domain"),
        "period": project.data.get("period"),
        "repo_url": project.data.get("repo_url"),
        "demo_url": project.data.get("demo_url"),
        "company_name": project.data.get("company_name"),
        "technologies": list(set(tech_names)),
        "achievements": achievements,
    }

    sources = [_node_to_source(project)] + [_node_to_source(t) for t in techs[:5]]

    return GraphQueryResult(
        items=[item],
        found=True,
        sources=sources,
        confidence=0.9,
        intent=Intent.PROJECT_DETAILS,
        entity_key=entity_key,
    )


def _experience_query(entity_key: str | None) -> GraphQueryResult:
    """Запрос опыта работы."""
    store = get_graph_store()
    companies = store.get_nodes_by_type(NodeType.COMPANY)

    if entity_key:
        key_lower = entity_key.lower()
        companies = [c for c in companies
                     if key_lower in c.slug.lower() or key_lower in c.name.lower()]

    items = []
    for c in companies:
        # Получаем проекты компании
        projects = []
        for p in store.get_nodes_by_type(NodeType.PROJECT):
            if p.data.get("company_slug") == c.slug:
                projects.append(p.name)

        items.append({
            "company": c.name,
            "role": c.data.get("role"),
            "period": f"{c.data.get('start_date')} - {c.data.get('end_date') or 'present'}",
            "is_current": c.data.get("is_current"),
            "projects": projects,
        })

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=[_node_to_source(c) for c in companies[:10]],
        confidence=0.9 if items else 0.0,
        intent=Intent.EXPERIENCE,
        entity_key=entity_key,
    )


def graph_query(intent: Intent, entity_key: str | None = None) -> GraphQueryResult:
    """
    Выполнить запрос к графу знаний.

    Args:
        intent: Намерение (тип запроса)
        entity_key: Опциональный slug сущности для фильтрации

    Returns:
        GraphQueryResult со структурированными фактами
    """
    handlers = {
        Intent.ACHIEVEMENTS: lambda: _achievements_query(entity_key),
        Intent.CURRENT_JOB: _current_job_query,
        Intent.CONTACTS: _contacts_query,
        Intent.LANGUAGES: _languages_query,
        Intent.TECHNOLOGIES: lambda: _technologies_query(entity_key),
        Intent.PROJECT_DETAILS: lambda: _project_details_query(entity_key or ""),
        Intent.EXPERIENCE: lambda: _experience_query(entity_key),
    }

    handler = handlers.get(intent)
    if handler:
        return handler()

    # Default: пустой результат для неподдерживаемых intent'ов
    return GraphQueryResult(
        items=[],
        found=False,
        sources=[],
        confidence=0.0,
        intent=intent,
        entity_key=entity_key,
    )
