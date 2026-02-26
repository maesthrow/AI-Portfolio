"""
FactNormalizer - детерминированная фильтрация фактов.

Применяет правила нормализации согласно intent и tech_filter.
Это P0 требование для устранения галлюцинаций типа "MySQL вероятно".
"""
from __future__ import annotations

import logging
import re
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

# Common technology abbreviation mappings (canonical English → abbreviations/translations)
# NOTE: "CV" excluded from Computer Vision — ambiguous with "curriculum vitae"
# (e.g. "Отправка CV через диалог" would false-positive match).
TECH_ABBREVIATIONS: dict[str, list[str]] = {
    "Computer Vision": ["компьютерное зрение", "компьютерн"],
    "Machine Learning": ["ML", "машинное обучение", "машинн"],
    "Natural Language Processing": ["NLP", "обработка естественного языка"],
    "Artificial Intelligence": ["AI", "ИИ", "искусственный интеллект"],
    "Deep Learning": ["DL", "глубокое обучение"],
    "Named Entity Recognition": ["NER"],
    "Optical Character Recognition": ["OCR"],
    "Large Language Model": ["LLM", "языковая модель"],
}


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
        entity_names: list[str] | None = None,
        question: str | None = None,
    ) -> NormalizerOutput:
        """
        Apply deterministic normalization rules to facts.

        Args:
            facts: List of facts from tool execution
            intent: Query intent
            tech_filter: Technology filter parameters
            max_items: Maximum number of items to return
            entity_names: Technology entity names from planner (for content filtering)
            question: Original user question (for keyword extraction)

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
            # Filter to only technology_usage fact types.
            # experience and experience_project are included because technology usage
            # is often described in job achievements and project descriptions.
            tech_facts = [f for f in filtered if f.type in (
                "technology_usage", "technology", "project",
                "experience", "experience_project",
            )]
            if tech_facts:
                filtered = tech_facts
                rules_applied.append("technology_usage_filter")

            # === Rule 2b: Content-level bullet filtering ===
            if entity_names:
                keywords = self._build_content_keywords(entity_names, question)
                if keywords:
                    content_filtered = []
                    for fact in filtered:
                        new_text = self._filter_fact_bullets(fact.text, keywords)
                        if new_text is not None:
                            if new_text != fact.text:
                                fact = FactItem(
                                    type=fact.type,
                                    text=new_text,
                                    metadata=fact.metadata,
                                    source_id=fact.source_id,
                                )
                            content_filtered.append(fact)
                    if content_filtered:
                        filtered = content_filtered
                        rules_applied.append("technology_usage_content_filter")

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

    @staticmethod
    def _build_content_keywords(
        entity_names: list[str],
        question: str | None = None,
    ) -> set[str]:
        """Build keyword set for content-level bullet filtering.

        Combines three sources:
        1. Entity names from planner (split into words + full phrase)
        2. Abbreviation mappings from TECH_ABBREVIATIONS (bidirectional)
        3. Significant tokens from original question (stem-like prefix)
        """
        keywords: set[str] = set()

        for name in (entity_names or []):
            name_lower = name.strip().lower()
            if not name_lower:
                continue
            keywords.add(name_lower)
            for word in name_lower.split():
                if len(word) >= 2:
                    keywords.add(word)

            # Check TECH_ABBREVIATIONS bidirectionally
            for canonical, abbrevs in TECH_ABBREVIATIONS.items():
                canonical_lower = canonical.lower()
                abbrevs_lower = [a.lower() for a in abbrevs]

                if canonical_lower == name_lower:
                    # Forward: entity name IS the canonical name
                    for abbr in abbrevs_lower:
                        keywords.add(abbr)
                elif name_lower in abbrevs_lower:
                    # Reverse: entity name IS one of the abbreviations
                    keywords.add(canonical_lower)
                    for word in canonical_lower.split():
                        if len(word) >= 2:
                            keywords.add(word)
                    for abbr in abbrevs_lower:
                        keywords.add(abbr)

        # Extract significant tokens from question
        if question:
            tokens = re.findall(r'[\w]+', question.lower())
            for token in tokens:
                if len(token) < 3:
                    continue
                # Simple stem: remove likely case endings for long words
                if len(token) >= 6:
                    stem = token[: len(token) - 2]
                else:
                    stem = token
                keywords.add(stem)

        return keywords

    @staticmethod
    def _filter_fact_bullets(
        fact_text: str,
        keywords: set[str],
    ) -> str | None:
        """Filter bullet points in fact text by keyword relevance.

        Header lines (non-bullets) are always preserved.
        Bullet lines (starting with '- ' or '\\u2022 ') are kept only
        if they contain any keyword as a case-insensitive substring.

        For facts WITHOUT bullets (e.g. technology descriptions, project headers),
        check if ANY line contains a keyword — if not, the entire fact is excluded.

        Returns:
            Filtered text with only matching bullets, or None if no content matched.
        """
        if not fact_text or not keywords:
            return None

        lines = fact_text.split('\n')
        result: list[str] = []
        total_bullets = 0
        matched_bullets = 0

        for line in lines:
            stripped = line.strip()
            is_bullet = stripped.startswith('- ') or stripped.startswith('\u2022 ')

            if is_bullet:
                total_bullets += 1
                line_lower = stripped.lower()
                if any(kw in line_lower for kw in keywords):
                    matched_bullets += 1
                    result.append(line)
            else:
                result.append(line)

        if total_bullets == 0:
            # No bullets — check if any line mentions a keyword.
            # This prevents irrelevant non-bulleted facts (e.g. F3 TAIL project)
            # from passing through when they have nothing to do with the query.
            full_lower = fact_text.lower()
            if any(kw in full_lower for kw in keywords):
                return fact_text
            return None

        if matched_bullets == 0:
            return None

        return '\n'.join(result).strip()


def normalize_facts(
    facts: list[FactItem],
    intent: str | IntentV3,
    tech_filter: TechFilter | None = None,
    max_items: int = 20,
    entity_names: list[str] | None = None,
    question: str | None = None,
) -> NormalizerOutput:
    """
    Convenience function for fact normalization.

    Args:
        facts: Facts from tool execution
        intent: Query intent
        tech_filter: Technology filter
        max_items: Maximum items
        entity_names: Technology entity names from planner (for content filtering)
        question: Original user question (for keyword extraction)

    Returns:
        NormalizerOutput
    """
    normalizer = FactNormalizer()
    return normalizer.normalize(facts, intent, tech_filter, max_items, entity_names, question)
