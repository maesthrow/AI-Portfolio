"""
Graph Query - запросы к графу знаний.

Функции для извлечения структурированных фактов из графа
по различным Intent'ам.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..rag.search_types import Intent, GraphQueryResult
from .schema import NodeType, EdgeType, GraphNode
from .store import get_graph_store

logger = logging.getLogger(__name__)

# Human-readable category names for Answer LLM context
CATEGORY_DISPLAY_NAMES = {
    "language": "языки программирования",
    "database": "базы данных",
    "vector_store": "векторные БД",
    "framework": "фреймворки",
    "ml_framework": "ML-фреймворки",
    "mlops": "MLOps-инструменты",
    "concept": "концепции",
    "tool": "инструменты",
    "message_broker": "брокеры сообщений",
    "library": "библиотеки",
    "cloud": "облачные сервисы",
    "other": "технологии",
}


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
    """
    Запрос текущего места работы.

    Приоритет:
    1. COMPANY nodes с is_current=True
    2. Fallback: profile.current_position из PERSON node
    """
    store = get_graph_store()

    # 1. Ищем компании с is_current=True
    companies = store.find_nodes_by_data(NodeType.COMPANY, "is_current", True)

    if companies:
        items = []
        for c in companies:
            start_date = c.data.get("start_date")
            role = c.data.get("role")
            summary_md = c.data.get("company_summary_md")
            role_md = c.data.get("company_role_md")

            # Формируем текст с датой начала
            header = f"{c.name} — {role}" if role else str(c.name)
            text_parts = [header]
            if start_date:
                text_parts.append(f"С {start_date} по настоящее время")
            if summary_md:
                text_parts.append(str(summary_md).strip())
            if role_md:
                text_parts.append(str(role_md).strip())

            items.append({
                "company": c.name,
                "role": role,
                "start_date": start_date,
                "company_summary_md": summary_md,
                "company_role_md": role_md,
                "text": "\n".join([p for p in text_parts if p]),
            })

        return GraphQueryResult(
            items=items,
            found=True,
            sources=[_node_to_source(c) for c in companies],
            confidence=0.95,
            intent=Intent.CURRENT_JOB,
        )

    # 2. Fallback: используем profile.current_position из PERSON node
    persons = store.get_nodes_by_type(NodeType.PERSON)
    if persons:
        person = persons[0]
        current_position = person.data.get("current_position")

        if current_position:
            logger.info(
                "current_job fallback to profile.current_position: %r",
                current_position[:50] if current_position else None,
            )
            return GraphQueryResult(
                items=[{
                    "current_position": current_position,
                    "name": person.name,
                    "text": f"Текущая позиция: {current_position}",
                }],
                found=True,
                sources=[_node_to_source(person)],
                confidence=0.90,
                intent=Intent.CURRENT_JOB,
            )

    # Нет данных о текущей работе
    return GraphQueryResult(
        items=[],
        found=False,
        sources=[],
        confidence=0.0,
        intent=Intent.CURRENT_JOB,
    )


def _contacts_query() -> GraphQueryResult:
    """Запрос контактной информации."""
    store = get_graph_store()
    contacts = store.get_nodes_by_type(NodeType.CONTACT)

    items = [
        {
            "kind": c.data.get("kind"),
            "label": c.data.get("value") or c.data.get("label") or c.name,
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


def _profile_query() -> GraphQueryResult:
    """
    Запрос информации о разработчике (PERSON node).

    Возвращает:
    - Имя, должность, subtitle
    - Summary, hero_description
    - Местоположение (location)
    - Текущая компания и роль
    - Топ-5 технологий (через KNOWS edges)
    """
    store = get_graph_store()
    persons = store.get_nodes_by_type(NodeType.PERSON)

    if not persons:
        logger.warning("No PERSON node found in graph")
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.PROFILE,
        )

    person = persons[0]  # Единственный PERSON в портфолио

    # Текущая компания
    current_company = None
    companies = store.get_nodes_by_type(NodeType.COMPANY)
    for c in companies:
        if c.data.get("is_current"):
            current_company = c
            break

    # Топ-5 технологий через KNOWS edges
    top_technologies = []
    knows_edges = store.get_outgoing_edges(person.id, EdgeType.KNOWS)
    tech_nodes = []
    for edge in knows_edges:
        tech = store.get_node(edge.target_id)
        if tech and tech.type == NodeType.TECHNOLOGY:
            tech_nodes.append(tech)

    # Сортируем по количеству использований в проектах
    tech_usage = []
    for t in tech_nodes:
        incoming = store.get_incoming_edges(t.id, EdgeType.USES)
        count = len([e for e in incoming if store.get_node(e.source_id)])
        tech_usage.append((t.name, count))

    tech_usage.sort(key=lambda x: x[1], reverse=True)
    top_technologies = [name for name, _ in tech_usage[:5]]

    item = {
        "name": person.name,
        "title": person.data.get("title"),
        "subtitle": person.data.get("subtitle"),
        "current_position": person.data.get("current_position"),
        "summary_md": person.data.get("summary_md"),
        "hero_headline": person.data.get("hero_headline"),
        "hero_description": person.data.get("hero_description"),
        "location": person.data.get("location"),
        "current_company": current_company.name if current_company else None,
        "current_role": current_company.data.get("role") if current_company else None,
        "top_technologies": top_technologies,
        "text": _build_profile_text(person, current_company, top_technologies),
    }

    sources = [_node_to_source(person)]
    if current_company:
        sources.append(_node_to_source(current_company))

    return GraphQueryResult(
        items=[item],
        found=True,
        sources=sources,
        confidence=0.95,
        intent=Intent.PROFILE,
    )


def _build_profile_text(
    person: GraphNode,
    current_company: GraphNode | None,
    top_technologies: list[str],
) -> str:
    """Собрать текстовое описание профиля для Answer LLM."""
    parts = []

    # Имя и должность
    name = person.name
    title = person.data.get("title") or ""
    if title:
        parts.append(f"{name} — {title}")
    else:
        parts.append(name)

    # Subtitle
    subtitle = person.data.get("subtitle")
    if subtitle:
        parts.append(subtitle)

    # Текущая позиция
    current_position = person.data.get("current_position")
    if current_position:
        parts.append(f"Текущая позиция: {current_position}")
    elif current_company:
        role = current_company.data.get("role") or ""
        parts.append(f"Текущая позиция: {role} в {current_company.name}")

    # Местоположение
    location = person.data.get("location")
    if location:
        parts.append(f"Местоположение: {location}")

    # Summary
    summary = person.data.get("summary_md")
    if summary:
        parts.append(summary)

    # Hero description
    hero_desc = person.data.get("hero_description")
    if hero_desc and hero_desc != summary:
        parts.append(hero_desc)

    # Топ технологии
    if top_technologies:
        parts.append(f"Ключевые технологии: {', '.join(top_technologies)}")

    return "\n".join(parts)


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
        node = store.get_node_by_slug(entity_key)

        # Technology usage: if entity_key refers to a technology node, list projects that USE it.
        if node and node.type == NodeType.TECHNOLOGY:
            tech = node
            incoming = store.get_incoming_edges(tech.id, EdgeType.USES)
            projects = [store.get_node(e.source_id) for e in incoming]
            projects = [p for p in projects if p and p.type == NodeType.PROJECT]

            items = [
                {
                    "technology": tech.name,
                    "project": p.name,
                    "project_slug": p.slug,
                    "company_name": p.data.get("company_name"),
                    "domain": p.data.get("domain"),
                }
                for p in projects
            ]
            sources = [_node_to_source(tech)] + [_node_to_source(p) for p in projects[:10]]

            return GraphQueryResult(
                items=items,
                found=len(items) > 0,
                sources=sources,
                confidence=0.9 if items else 0.0,
                intent=Intent.TECHNOLOGIES,
                entity_key=entity_key,
            )

        project = node if (node and node.type == NodeType.PROJECT) else None
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

        # CRITICAL FIX: If entity_key provided but not found, return empty result
        # This allows fallback to vector search instead of returning all technologies
        logger.warning(
            "Entity key '%s' not found in graph for technology query, returning empty result for fallback",
            entity_key
        )
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.TECHNOLOGIES,
            entity_key=entity_key,
        )

    # Все технологии (only when NO entity_key specified)
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

    node = store.get_node_by_slug(entity_key)
    project = node if (node and node.type == NodeType.PROJECT) else None

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

        summary_md = c.data.get("company_summary_md")
        role_md = c.data.get("company_role_md")
        role = c.data.get("role")
        start_date = c.data.get("start_date")
        end_date = c.data.get("end_date")
        is_current = c.data.get("is_current")

        # Формируем читаемый период
        if start_date and end_date:
            period = f"{start_date} — {end_date}"
        elif start_date and is_current:
            period = f"{start_date} — настоящее время"
        elif start_date:
            period = f"с {start_date}"
        else:
            period = None

        # Формируем текст с датами
        header = f"{c.name} — {role}" if role else str(c.name)
        text_parts = [header]
        if period:
            text_parts.append(f"Период: {period}")
        if summary_md:
            text_parts.append(str(summary_md))
        if role_md:
            text_parts.append(str(role_md))

        items.append({
            "company": c.name,
            "role": role,
            "period": period,
            "is_current": c.data.get("is_current"),
            "projects": projects,
            "company_summary_md": summary_md,
            "company_role_md": role_md,
            "text": "\n".join([p for p in text_parts if p]),
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
        Intent.PROFILE: _profile_query,
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


def graph_query_with_filters(
    intent: Intent,
    entity_key: str | None = None,
    tech_category: str | None = None,
    company_key: str | None = None,
    project_key: str | None = None,
    limit: int = 20,
) -> GraphQueryResult:
    """
    Выполнить запрос к графу с дополнительными фильтрами.

    Фильтрует результаты по:
    - tech_category: категория технологии из node.data["category"]
    - company_key: фильтр по компании
    - project_key: фильтр по проекту

    Args:
        intent: Намерение (тип запроса)
        entity_key: Опциональный slug сущности
        tech_category: Категория технологий (language/database/framework/etc.)
        company_key: Slug компании для фильтрации
        project_key: Slug проекта для фильтрации
        limit: Максимальное количество результатов

    Returns:
        GraphQueryResult с отфильтрованными фактами
    """
    store = get_graph_store()

    # === Handle technology queries with category filter ===
    # CRITICAL FIX: When tech_category is specified, return PROJECTS using those technologies
    # This fixes "ML проекты" returning technology list instead of project list
    if intent == Intent.TECHNOLOGIES and tech_category:
        logger.info(
            "Technology query with category filter '%s' - returning PROJECTS using these technologies",
            tech_category
        )
        return _projects_by_tech_category_query(tech_category, limit)

    if intent == Intent.LANGUAGES:
        # Languages - return technologies in language category
        # Note: This returns technologies, not projects (semantic difference)
        return _technologies_by_category_query("language", limit)

    # === Handle experience queries with company filter ===
    if intent == Intent.EXPERIENCE and company_key:
        return _experience_query(company_key)

    # === Handle achievements with company/project filter ===
    if intent == Intent.ACHIEVEMENTS:
        key = project_key or company_key or entity_key
        return _achievements_query(key)

    # === Default: use base query ===
    return graph_query(intent, entity_key)


def _technologies_by_category_query(
    category: str,
    limit: int = 20
) -> GraphQueryResult:
    """
    Запрос технологий по категории из data["category"].

    Фильтрует ТОЛЬКО по реальной категории из данных,
    без хардкода.

    ВАЖНО: Сортирует по количеству использования (число проектов)
    для корректного ранжирования (Python с 5 проектами > C# с 1 проектом).
    """
    store = get_graph_store()
    techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)

    # Filter by category from node.data
    category_lower = category.lower()
    filtered = []
    for t in techs:
        node_category = (t.data.get("category") or "").lower()
        if node_category == category_lower:
            filtered.append(t)

    # If no matches, return empty
    if not filtered:
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.TECHNOLOGIES,
            entity_key=category,
        )

    # CRITICAL: Sort by usage count (number of projects using this technology)
    # This ensures Python (5+ projects) appears before C# (1 project)
    tech_usage_counts = []
    for t in filtered:
        # Count incoming USES edges from projects
        incoming_edges = store.get_incoming_edges(t.id, EdgeType.USES)
        project_count = len([
            e for e in incoming_edges
            if store.get_node(e.source_id) and store.get_node(e.source_id).type == NodeType.PROJECT
        ])
        tech_usage_counts.append((t, project_count))

    # Sort by usage count descending (most used first)
    tech_usage_counts.sort(key=lambda x: x[1], reverse=True)

    # Apply limit after sorting
    top_techs = tech_usage_counts[:limit]

    items = [
        {
            "name": t.name,
            "category": t.data.get("category"),
            "project_count": count,  # Include count for debugging
        }
        for t, count in top_techs
    ]

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=[_node_to_source(t) for t, _ in top_techs[:10]],
        confidence=0.95 if items else 0.0,
        intent=Intent.TECHNOLOGIES,
        entity_key=category,
    )


def _projects_by_tech_category_query(
    category: str,
    limit: int = 20
) -> GraphQueryResult:
    """
    Запрос проектов, использующих технологии из категории.

    Возвращает проекты с указанием технологий из данной категории,
    которые в них применяются.

    Пример: category="ml_framework" вернёт проекты t2, AI-Portfolio, HyperKeeper
    с указанием ML-технологий, использованных в каждом проекте.

    Args:
        category: Категория технологий (ml_framework, language, database, etc.)
        limit: Максимальное количество проектов

    Returns:
        GraphQueryResult с проектами, отсортированными по количеству
        использованных технологий из данной категории
    """
    store = get_graph_store()

    # 1. Get all technologies in this category
    techs = store.get_nodes_by_type(NodeType.TECHNOLOGY)
    category_lower = category.lower()
    filtered_techs = [
        t for t in techs
        if (t.data.get("category") or "").lower() == category_lower
    ]

    if not filtered_techs:
        logger.warning(
            "No technologies found for category '%s', cannot find projects",
            category
        )
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.TECHNOLOGIES,
            entity_key=category,
        )

    logger.info(
        "Found %d technologies in category '%s': %s",
        len(filtered_techs),
        category,
        [t.name for t in filtered_techs[:5]]
    )

    # 2. For each technology, get projects using it
    project_tech_map = {}  # project_id -> {project: GraphNode, technologies: [str]}

    for tech in filtered_techs:
        incoming_edges = store.get_incoming_edges(tech.id, EdgeType.USES)
        for edge in incoming_edges:
            source_node = store.get_node(edge.source_id)
            if source_node and source_node.type == NodeType.PROJECT:
                if source_node.id not in project_tech_map:
                    project_tech_map[source_node.id] = {
                        "project": source_node,
                        "technologies": []
                    }
                project_tech_map[source_node.id]["technologies"].append(tech.name)

    if not project_tech_map:
        logger.warning(
            "No projects found using technologies from category '%s'",
            category
        )
        return GraphQueryResult(
            items=[],
            found=False,
            sources=[],
            confidence=0.0,
            intent=Intent.TECHNOLOGIES,
            entity_key=category,
        )

    logger.info(
        "Found %d projects using technologies from category '%s'",
        len(project_tech_map),
        category
    )

    # 3. Sort projects by number of technologies from this category (descending)
    projects_sorted = sorted(
        project_tech_map.values(),
        key=lambda x: len(x["technologies"]),
        reverse=True
    )

    # 4. Apply limit
    top_projects = projects_sorted[:limit]

    # 5. Build result items
    items = []
    sources = []
    for entry in top_projects:
        project = entry["project"]
        techs_used = entry["technologies"]

        # Build text field with project info and technologies
        company_str = project.data.get("company_name") or "standalone"
        tech_list = ", ".join(techs_used[:3])
        if len(techs_used) > 3:
            tech_list += f" и ещё {len(techs_used) - 3}"

        items.append({
            "name": project.name,  # For compatibility with _item_to_fact
            "project": project.name,  # Additional field
            "project_slug": project.slug,
            "slug": project.slug,  # For compatibility
            "company_name": project.data.get("company_name"),
            "domain": project.data.get("domain"),
            "period": project.data.get("period"),
            "description": project.data.get("description_md"),
            "technologies": techs_used,
            "tech_count": len(techs_used),
            "category": category,
            "text": f"{project.name} ({company_str}) — использует {CATEGORY_DISPLAY_NAMES.get(category, 'технологии')}: {tech_list}",
        })
        sources.append(_node_to_source(project))

    logger.info(
        "Returning %d projects for category '%s': %s",
        len(items),
        category,
        [item["project"] for item in items[:5]]
    )

    return GraphQueryResult(
        items=items,
        found=len(items) > 0,
        sources=sources[:10],
        confidence=0.9 if items else 0.0,
        intent=Intent.TECHNOLOGIES,
        entity_key=category,
    )
