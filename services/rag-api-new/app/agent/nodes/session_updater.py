"""
Session Updater Node - updates session state after answer.

Extracts entities from normalized_facts and saves to state for
context persistence between questions.

Part of P0: Session context management.
"""
from __future__ import annotations

import logging
from typing import Any

from ..state import RAGState

logger = logging.getLogger(__name__)


def session_updater_node(state: RAGState) -> dict[str, Any]:
    """
    Update session state after answer generation.

    Extracts company/project entities from normalized_facts
    and saves them to session state for future questions.

    This enables context-aware queries like:
    - "над чем работал в Aston" -> last_company = "aston"
    - "а какой там стек?" -> uses last_company from previous question

    Args:
        state: Current RAG state

    Returns:
        State update with last_company, last_project, context_entities
    """
    normalized_facts = state.get("normalized_facts", [])
    merged_facts = state.get("merged_facts", [])

    # Start with existing values
    last_company = state.get("last_company")
    last_project = state.get("last_project")
    last_technology = state.get("last_technology")
    context_entities = list(state.get("context_entities", []))

    # Track what we find in this response
    found_companies: set[str] = set()
    found_projects: set[str] = set()
    found_technologies: set[str] = set()

    logger.info(
        "SessionUpdater input: normalized_facts=%d, merged_facts=%d",
        len(normalized_facts),
        len(merged_facts),
    )

    # Process normalized_facts (higher priority)
    for i, fact in enumerate(normalized_facts):
        # Handle both object attributes and dict access
        if isinstance(fact, dict):
            md = fact.get("metadata", {}) or {}
        else:
            md = getattr(fact, "metadata", {}) or {}

        if i < 3:
            logger.info(
                "SessionUpdater fact[%d]: type=%s, md_keys=%s",
                i,
                type(fact).__name__,
                list(md.keys())[:10] if isinstance(md, dict) else "N/A",
            )

        if isinstance(md, dict):
            _extract_entities_from_metadata(
                md, found_companies, found_projects, found_technologies
            )

    # Fallback to merged_facts if no normalized_facts
    if not normalized_facts:
        for fact in merged_facts:
            md = getattr(fact, "metadata", {}) or {}
            if isinstance(md, dict):
                _extract_entities_from_metadata(
                    md, found_companies, found_projects, found_technologies
                )

    # Update last_company (most recent takes priority)
    if found_companies:
        last_company = list(found_companies)[0]
        logger.debug("Updated last_company: %s", last_company)

    # Update last_project
    if found_projects:
        last_project = list(found_projects)[0]
        logger.debug("Updated last_project: %s", last_project)

    # Update last_technology
    if found_technologies:
        last_technology = list(found_technologies)[0]
        logger.debug("Updated last_technology: %s", last_technology)

    # Update context_entities (append new ones)
    for company in found_companies:
        entity = {"type": "company", "slug": company}
        if entity not in context_entities:
            context_entities.append(entity)

    for project in found_projects:
        entity = {"type": "project", "slug": project}
        if entity not in context_entities:
            context_entities.append(entity)

    for tech in found_technologies:
        entity = {"type": "technology", "slug": tech}
        if entity not in context_entities:
            context_entities.append(entity)

    # Limit context_entities to prevent unbounded growth
    if len(context_entities) > 20:
        context_entities = context_entities[-20:]

    logger.info(
        "SessionUpdater found: companies=%s, projects=%s, technologies=%s",
        list(found_companies)[:5],
        list(found_projects)[:5],
        list(found_technologies)[:5],
    )

    logger.info(
        "SessionUpdater: last_company=%s, last_project=%s, entities=%d",
        last_company,
        last_project,
        len(context_entities),
    )

    return {
        "last_company": last_company,
        "last_project": last_project,
        "last_technology": last_technology,
        "context_entities": context_entities,
    }


def _extract_entities_from_metadata(
    md: dict,
    found_companies: set,
    found_projects: set,
    found_technologies: set,
) -> None:
    """
    Extract entity slugs from fact metadata.

    Handles various document types from the RAG pipeline:
    - experience, experience_project: contain company_slug, project_slug
    - project: contains slug, company_slug
    - technology: contains name, slug, category
    - stat, work_approach: may contain company references
    """
    doc_type = md.get("type", "")

    # === Company extraction ===
    # Priority: company_slug > company_name (normalized)
    company_slug = md.get("company_slug")
    if company_slug:
        found_companies.add(_normalize_slug(company_slug))

    company_name = md.get("company_name")
    if company_name and not company_slug:
        found_companies.add(_normalize_slug(company_name))

    # === Project extraction ===
    # Accept project_slug from experience_project, or slug from project docs
    # Don't filter by type - we want to capture all project references
    project_slug = md.get("project_slug")
    if project_slug:
        found_projects.add(_normalize_slug(project_slug))

    # For standalone project documents, use "slug" field
    # But only if it looks like a project (not a technology or company)
    if doc_type in ("project", "experience_project"):
        slug = md.get("slug")
        if slug and not project_slug:
            found_projects.add(_normalize_slug(slug))

    # === Technology extraction ===
    # From technology documents
    if doc_type == "technology":
        tech_slug = md.get("slug")
        tech_name = md.get("name")
        if tech_slug:
            found_technologies.add(_normalize_slug(tech_slug))
        elif tech_name:
            found_technologies.add(_normalize_slug(tech_name))

    # From technologies array in project/experience documents
    technologies = md.get("technologies", [])
    if isinstance(technologies, list):
        for tech in technologies[:5]:  # Limit to prevent noise
            if isinstance(tech, str):
                found_technologies.add(_normalize_slug(tech))


def _normalize_slug(value: str) -> str:
    """Normalize a value to slug format (lowercase, no spaces)."""
    if not value:
        return ""
    return value.lower().strip().replace(" ", "-")
