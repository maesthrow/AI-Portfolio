"""
FactBundleBuilder - построение FactBundle из фактов.

Извлекает именованные сущности для проверки grounding.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from ..planner.schemas import FactItem
from ..planner.schemas_v3 import FactBundle, FactBundleItem, TechCategory

logger = logging.getLogger(__name__)


class FactBundleBuilder:
    """
    Builds FactBundle from facts with entity extraction.

    Extracts:
    - Technologies (from metadata.category or known patterns)
    - Companies (from metadata.company_name)
    - Projects (from metadata.name, metadata.project_name)
    - Roles (from metadata.role)
    - Dates (from metadata.start_date, period, etc.)
    """

    def __init__(self):
        pass

    def build(self, facts: list[FactItem]) -> FactBundle:
        """
        Build FactBundle from list of facts.

        Args:
            facts: List of FactItem from tool execution

        Returns:
            FactBundle with extracted entities
        """
        bundle_items: list[FactBundleItem] = []
        technologies: set[str] = set()
        companies: set[str] = set()
        projects: set[str] = set()
        roles: set[str] = set()
        dates: set[str] = set()

        for fact in facts:
            # Convert FactItem to FactBundleItem
            category = self._extract_category(fact)
            bundle_item = FactBundleItem(
                type=fact.type,
                text=fact.text,
                entity_id=fact.source_id,
                category=category,
                metadata=fact.metadata,
            )
            bundle_items.append(bundle_item)

            # Extract entities from metadata
            md = fact.metadata or {}

            # Technologies
            tech_name = md.get("name") or md.get("technology")
            if fact.type in ("technology", "technology_usage") and tech_name:
                technologies.add(str(tech_name))

            tech_list = md.get("technologies", [])
            if isinstance(tech_list, list):
                technologies.update(str(t) for t in tech_list if t)
            elif isinstance(tech_list, str):
                technologies.update(t.strip() for t in tech_list.split(",") if t.strip())

            # Companies
            company = md.get("company_name") or md.get("company")
            if company:
                companies.add(str(company))

            # Projects
            project = md.get("project_name") or md.get("project") or md.get("name")
            if fact.type in ("project", "experience_project", "achievement") and project:
                projects.add(str(project))

            # Roles
            role = md.get("role")
            if role:
                roles.add(str(role))

            # Dates
            for date_key in ("start_date", "end_date", "period"):
                date_val = md.get(date_key)
                if date_val:
                    dates.add(str(date_val))

            # Extract from text as well
            self._extract_from_text(fact.text, technologies, companies, projects)

        return FactBundle(
            facts=bundle_items,
            technologies=sorted(technologies),
            companies=sorted(companies),
            projects=sorted(projects),
            roles=sorted(roles),
            dates=sorted(dates),
        )

    def _extract_category(self, fact: FactItem) -> TechCategory | None:
        """Extract technology category from fact metadata."""
        md = fact.metadata or {}
        category = md.get("category")

        if not category:
            return None

        category_lower = str(category).lower()

        # Map to TechCategory enum
        category_map = {
            "language": TechCategory.LANGUAGE,
            "database": TechCategory.DATABASE,
            "framework": TechCategory.FRAMEWORK,
            "ml_framework": TechCategory.ML_FRAMEWORK,
            "tool": TechCategory.TOOL,
            "cloud": TechCategory.CLOUD,
            "library": TechCategory.LIBRARY,
            "concept": TechCategory.CONCEPT,
        }

        return category_map.get(category_lower, TechCategory.OTHER)

    def _extract_from_text(
        self,
        text: str,
        technologies: set[str],
        companies: set[str],
        projects: set[str],
    ) -> None:
        """
        Best-effort extraction of entities from text.

        Uses patterns to find common entity mentions.
        """
        if not text:
            return

        # Common technology patterns
        # Match quoted names or capitalized words
        quoted = re.findall(r'"([^"]+)"', text)
        for q in quoted:
            if len(q) > 2 and len(q) < 50:
                # Could be a technology or project name
                if any(kw in q.lower() for kw in ["проект", "project"]):
                    projects.add(q)
                else:
                    # Assume technology
                    technologies.add(q)

        # Company patterns: "в компании X", "@ X"
        company_patterns = [
            r"в компании\s+([А-Яа-яA-Za-z0-9\-_]+)",
            r"@\s*([А-Яа-яA-Za-z0-9\-_]+)",
            r"компания\s+([А-Яа-яA-Za-z0-9\-_]+)",
        ]
        for pattern in company_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            companies.update(matches)

        # Project patterns: "проект X", "на проекте X"
        project_patterns = [
            r"проект[еа]?\s+([А-Яа-яA-Za-z0-9\-_]+)",
            r"на проекте\s+([А-Яа-яA-Za-z0-9\-_]+)",
        ]
        for pattern in project_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            projects.update(matches)


def build_fact_bundle(facts: list[FactItem]) -> FactBundle:
    """
    Convenience function to build FactBundle.

    Args:
        facts: List of facts from tool execution

    Returns:
        FactBundle with extracted entities
    """
    builder = FactBundleBuilder()
    return builder.build(facts)
