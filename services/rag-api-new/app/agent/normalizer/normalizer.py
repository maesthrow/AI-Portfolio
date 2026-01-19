"""
FactNormalizer - детерминированная фильтрация фактов.

Применяет правила нормализации согласно intent и tech_filter.
Это P0 требование для устранения галлюцинаций типа "MySQL вероятно".
"""
from __future__ import annotations

import logging
from typing import Any

from ..planner.schemas import FactItem, FactsPayload
from ..planner.schemas_v3 import (
    IntentV3,
    TechFilter,
    TechCategory,
    NormalizerOutput,
    FactBundleItem,
)
from .fact_bundle import build_fact_bundle

logger = logging.getLogger(__name__)

# Types that are NOT places where technologies are applied
# These should be excluded from technology_usage answers
EXCLUDED_TYPES_FOR_TECH_USAGE = frozenset({
    "focus_area",      # Skill descriptions, not projects
    "work_approach",   # Work methodologies, not projects
    "stat",            # Statistics
    "catalog",         # Technology catalogs
    "tech_focus",      # Technology focus areas
})

# Types that don't provide direct project information
# These are excluded from project_list answers (but technology can be kept if it references projects)
EXCLUDED_TYPES_FOR_PROJECT_LIST = frozenset({
    "focus_area",      # Skill descriptions
    "work_approach",   # Work methodologies
    "stat",            # Statistics (like "5+ ML-проектов")
    "catalog",         # Technology catalogs
    "tech_focus",      # Technology focus areas
})


class FactNormalizer:
    """
    Deterministic fact normalizer.

    Applies filtering rules based on:
    - Intent (technology_overview vs technology_usage vs experience_summary)
    - TechFilter (category, tags_any, strict)

    Key rules from TZ section 10:
    - technology_overview + category=database → only database technologies
    - technology_overview + category=language → only language technologies
    - technology_usage + technology_key=rag → only projects with RAG
    """

    def __init__(self):
        pass

    def normalize(
        self,
        facts: list[FactItem],
        intent: str | IntentV3,
        tech_filter: TechFilter | None = None,
        max_items: int = 20,
        entity_scope: list | None = None,
    ) -> NormalizerOutput:
        """
        Apply deterministic normalization rules to facts.

        Args:
            facts: List of facts from tool execution
            intent: Query intent
            tech_filter: Technology filter parameters
            max_items: Maximum number of items to return
            entity_scope: P2 FIX - List of entities for scoped filtering

        Returns:
            NormalizerOutput with filtered facts and metadata
        """
        if not facts:
            return NormalizerOutput(
                filtered_facts=[],
                removed_count=0,
                rules_applied=[],
                rendered_text="",
            )

        intent_str = intent.value if isinstance(intent, IntentV3) else str(intent).lower()
        rules_applied: list[str] = []
        filtered = facts.copy()
        original_count = len(filtered)

        # Debug: log fact types distribution
        type_counts: dict[str, int] = {}
        for f in filtered:
            type_counts[f.type] = type_counts.get(f.type, 0) + 1
        logger.debug(f"Normalizer input fact types: {type_counts}")

        # === Rule 1: Technology overview with category filter ===
        if intent_str == "technology_overview" and tech_filter and tech_filter.category:
            category = tech_filter.category
            category_str = category.value if isinstance(category, TechCategory) else str(category).lower()

            if tech_filter.strict:
                # STRICT: only return exact category matches
                filtered = self._filter_by_category_strict(filtered, category_str)
                rules_applied.append(f"strict_category_filter:{category_str}")
            else:
                # BOOST: prioritize matching categories
                filtered = self._boost_by_category(filtered, category_str)
                rules_applied.append(f"boost_category_filter:{category_str}")

        # === Rule 2: Technology usage - filter and prioritize ===
        if intent_str == "technology_usage":
            # Step 1: Exclude non-project types (focus_area, work_approach, etc.)
            before_exclude = len(filtered)
            filtered = [f for f in filtered if f.type not in EXCLUDED_TYPES_FOR_TECH_USAGE]
            excluded_count = before_exclude - len(filtered)
            if excluded_count > 0:
                rules_applied.append(f"excluded_non_project_types:{excluded_count}")

            # Step 2: Prioritize facts about actual technology usage
            tech_facts = [f for f in filtered if f.type in ("technology_usage", "technology", "project")]
            other_facts = [f for f in filtered if f.type not in ("technology_usage", "technology", "project")]
            if tech_facts:
                filtered = tech_facts + other_facts
                rules_applied.append("technology_usage_prioritization")

        # === Rule 3: Experience summary - prioritize experience facts ===
        if intent_str == "experience_summary":
            exp_facts = [f for f in filtered if f.type in ("experience", "experience_project")]
            if exp_facts:
                # Prioritize experience facts, then others
                other_facts = [f for f in filtered if f.type not in ("experience", "experience_project")]
                filtered = exp_facts + other_facts
                rules_applied.append("experience_prioritization")

        # === Rule 4: Project list - smart filtering ===
        # Keep project facts as primary, but also include technology facts
        # that reference projects (they provide coverage of which projects exist)
        if intent_str == "project_list":
            # Step 1: Exclude noise types
            before_exclude = len(filtered)
            filtered = [f for f in filtered if f.type not in EXCLUDED_TYPES_FOR_PROJECT_LIST]
            excluded_count = before_exclude - len(filtered)
            if excluded_count > 0:
                rules_applied.append(f"project_list_excluded_noise:{excluded_count}")

            # Step 2: Categorize remaining facts
            project_facts = [f for f in filtered if f.type in ("project", "experience_project")]

            # Technology facts that reference projects (have project_names in metadata)
            tech_with_projects = []
            for f in filtered:
                if f.type == "technology":
                    md = f.metadata or {}
                    # Check if technology is used in projects
                    project_refs = md.get("project_names_csv") or md.get("project_names")
                    if project_refs:
                        tech_with_projects.append(f)

            # Experience facts (company-level, may mention projects)
            experience_facts = [f for f in filtered if f.type == "experience"]

            # Step 3: Build final list with priorities
            if project_facts:
                # Primary: project facts
                # Secondary: technology facts that mention projects (for coverage)
                # Tertiary: experience facts
                filtered = project_facts + tech_with_projects[:5] + experience_facts[:2]
                rules_applied.append("project_list_smart_filter")
            elif tech_with_projects:
                # Fallback: if no direct project facts, use technology facts
                filtered = tech_with_projects + experience_facts[:2]
                rules_applied.append("project_list_tech_fallback")
            elif experience_facts:
                # Last resort: experience facts
                filtered = experience_facts
                rules_applied.append("project_list_experience_fallback")

        # === P2 FIX: Rule 5: Entity scope filtering ===
        # Filter facts to match entity scope (e.g., only facts from specific company)
        if entity_scope:
            company_keys = self._extract_company_keys(entity_scope)
            if company_keys:
                before_scope = len(filtered)
                filtered = self._filter_by_company_scope(filtered, company_keys)
                scope_removed = before_scope - len(filtered)
                if scope_removed > 0:
                    rules_applied.append(f"entity_scope_filter:{company_keys[0]}:{scope_removed}")
                    logger.info(
                        "Entity scope filter applied: removed %d facts not matching companies %s",
                        scope_removed,
                        company_keys,
                    )

        # === Apply limit after filtering ===
        removed_by_limit = 0
        if len(filtered) > max_items:
            removed_by_limit = len(filtered) - max_items
            filtered = filtered[:max_items]
            rules_applied.append(f"limit_applied:{max_items}")

        # === Convert to FactBundleItem ===
        bundle_items = []
        for fact in filtered:
            category = self._get_category(fact)
            item = FactBundleItem(
                type=fact.type,
                text=fact.text,
                entity_id=fact.source_id,
                category=category,
                metadata=fact.metadata,
            )
            bundle_items.append(item)

        # === Render text ===
        rendered = self._render_facts(bundle_items)

        removed_count = original_count - len(filtered)

        logger.info(
            "Normalizer: %d -> %d facts, rules=%s",
            original_count,
            len(filtered),
            rules_applied,
        )

        return NormalizerOutput(
            filtered_facts=bundle_items,
            removed_count=removed_count,
            rules_applied=rules_applied,
            rendered_text=rendered,
        )

    def _filter_by_category_strict(
        self,
        facts: list[FactItem],
        category: str,
    ) -> list[FactItem]:
        """
        STRICT filtering: only return facts with exact category match.

        Simplified P2 version - relies on metadata.category from graph queries
        instead of hardcoded technology lists.

        For technology documents, checks metadata.category directly.
        For project documents, checks metadata.tech_category if present.
        """
        category_lower = category.lower()
        result = []

        for fact in facts:
            md = fact.metadata or {}
            fact_category = (md.get("category") or "").lower()
            tech_category = (md.get("tech_category") or "").lower()

            # Primary: check metadata.category
            if fact_category == category_lower:
                result.append(fact)
                continue

            # Projects tagged with tech_category from graph query
            if tech_category == category_lower:
                result.append(fact)
                continue

            # Fallback: check if category keyword mentioned in text
            if category_lower in fact.text.lower():
                result.append(fact)

        return result

    def _boost_by_category(
        self,
        facts: list[FactItem],
        category: str,
    ) -> list[FactItem]:
        """
        BOOST: prioritize facts with matching category.

        Returns matching facts first, then others.
        """
        category_lower = category.lower()
        matching = []
        other = []

        for fact in facts:
            md = fact.metadata or {}
            fact_category = (md.get("category") or "").lower()

            if fact_category == category_lower:
                matching.append(fact)
            else:
                other.append(fact)

        return matching + other

    def _get_category(self, fact: FactItem) -> TechCategory | None:
        """Extract TechCategory from fact metadata."""
        md = fact.metadata or {}
        category = md.get("category")

        if not category:
            return None

        category_lower = str(category).lower()
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

    def _render_facts(self, facts: list[FactBundleItem]) -> str:
        """Render facts as text for Answer LLM."""
        if not facts:
            return ""

        lines = []
        for fact in facts:
            type_label = f"[{fact.type}]"
            if fact.category:
                type_label = f"[{fact.type}:{fact.category.value}]"

            text = fact.text.strip()
            if len(text) > 500:
                text = text[:500] + "..."

            lines.append(f"{type_label} {text}")

        return "\n\n".join(lines)

    def _extract_company_keys(self, entity_scope: list) -> list[str]:
        """
        Extract company keys from entity scope.

        Handles both dict and object access patterns.
        Returns lowercase keys for case-insensitive matching.
        """
        company_keys = []
        for entity in entity_scope:
            entity_type = ""
            entity_id = ""

            if isinstance(entity, dict):
                entity_type = entity.get("type", "")
                entity_id = entity.get("id", "")
            elif hasattr(entity, "type"):
                entity_type = getattr(entity, "type", "")
                entity_id = getattr(entity, "id", "")

            if entity_type == "company" and entity_id:
                # Extract key from "company:aston" format
                if ":" in entity_id:
                    key = entity_id.split(":", 1)[1]
                else:
                    key = entity_id
                company_keys.append(key.lower())

        return company_keys

    def _filter_by_company_scope(
        self,
        facts: list[FactItem],
        company_keys: list[str],
    ) -> list[FactItem]:
        """
        Filter facts to only include those from specified companies.

        Facts without company info are kept (may be general facts).
        Facts with company info must match one of the company_keys.
        """
        result = []
        for fact in facts:
            md = fact.metadata or {}

            # Extract company info from fact metadata
            fact_company_slug = (md.get("company_slug") or "").lower()
            fact_company_name = (md.get("company_name") or "").lower()
            fact_company = fact_company_slug or fact_company_name

            # If fact has no company info, keep it (may be general fact)
            if not fact_company:
                result.append(fact)
                continue

            # Check if fact's company matches any of the scoped companies
            for key in company_keys:
                if key in fact_company or fact_company in key:
                    result.append(fact)
                    break

        return result


def normalize_facts(
    facts: list[FactItem],
    intent: str | IntentV3,
    tech_filter: TechFilter | None = None,
    max_items: int = 20,
    entity_scope: list | None = None,
) -> NormalizerOutput:
    """
    Convenience function for fact normalization.

    Args:
        facts: Facts from tool execution
        intent: Query intent
        tech_filter: Technology filter
        max_items: Maximum items
        entity_scope: P2 FIX - List of entities for scoped filtering

    Returns:
        NormalizerOutput
    """
    normalizer = FactNormalizer()
    return normalizer.normalize(facts, intent, tech_filter, max_items, entity_scope)
