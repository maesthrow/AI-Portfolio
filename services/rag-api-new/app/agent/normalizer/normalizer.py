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
    ) -> NormalizerOutput:
        """
        Apply deterministic normalization rules to facts.

        Args:
            facts: List of facts from tool execution
            intent: Query intent
            tech_filter: Technology filter parameters
            max_items: Maximum number of items to return

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

        # === Rule 2: Technology usage - only return projects with the technology ===
        if intent_str == "technology_usage":
            # Filter to only technology_usage fact types
            tech_facts = [f for f in filtered if f.type in ("technology_usage", "technology", "project")]
            if tech_facts:
                filtered = tech_facts
                rules_applied.append("technology_usage_filter")

        # === Rule 3: Experience summary - prioritize experience facts ===
        if intent_str == "experience_summary":
            exp_facts = [f for f in filtered if f.type in ("experience", "experience_project")]
            if exp_facts:
                # Prioritize experience facts, then others
                other_facts = [f for f in filtered if f.type not in ("experience", "experience_project")]
                filtered = exp_facts + other_facts
                rules_applied.append("experience_prioritization")

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

        For technology documents, checks metadata.category.
        Non-technology documents are excluded.
        """
        category_lower = category.lower()
        result = []

        for fact in facts:
            md = fact.metadata or {}
            fact_category = (md.get("category") or "").lower()

            # Only include if category matches
            if fact_category == category_lower:
                result.append(fact)
            # Include non-technology facts only if they reference the category
            elif fact.type not in ("technology", "technology_usage"):
                # Check if text mentions the category
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


def normalize_facts(
    facts: list[FactItem],
    intent: str | IntentV3,
    tech_filter: TechFilter | None = None,
    max_items: int = 20,
) -> NormalizerOutput:
    """
    Convenience function for fact normalization.

    Args:
        facts: Facts from tool execution
        intent: Query intent
        tech_filter: Technology filter
        max_items: Maximum items

    Returns:
        NormalizerOutput
    """
    normalizer = FactNormalizer()
    return normalizer.normalize(facts, intent, tech_filter, max_items)
