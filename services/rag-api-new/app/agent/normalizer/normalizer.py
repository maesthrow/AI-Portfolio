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

        # === Rule 4: Project list - prioritize project facts ===
        if intent_str == "project_list":
            project_facts = [f for f in filtered if f.type in ("project", "experience_project")]
            if project_facts:
                filtered = project_facts
                rules_applied.append("project_list_filter")

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

    # Known technologies by category for strict filtering of projects
    CATEGORY_TECHNOLOGIES = {
        "database": frozenset({
            "postgresql", "postgres", "ms sql server", "mssql", "sql server",
            "mongodb", "mongo", "redis", "chromadb", "chroma", "qdrant",
            "mysql", "sqlite", "oracle", "mariadb", "pgvector",
        }),
        "vector_store": frozenset({
            "chromadb", "chroma", "qdrant", "pgvector", "pinecone", "weaviate", "milvus",
        }),
        "ml_framework": frozenset({
            "langchain", "langgraph", "langsmith", "pytorch", "tensorflow", "keras",
            "scikit-learn", "sklearn", "huggingface", "transformers", "detectron2",
            "ultralytics", "yolo", "mlflow", "vllm", "gigachain", "llm", "rag",
        }),
        "message_broker": frozenset({
            "rabbitmq", "kafka", "redis", "celery", "nats",
        }),
    }

    def _filter_by_category_strict(
        self,
        facts: list[FactItem],
        category: str,
    ) -> list[FactItem]:
        """
        STRICT filtering: only return facts with exact category match.

        For technology documents, checks metadata.category.
        For project/experience documents, checks if technologies include
        any from the target category.
        """
        category_lower = category.lower()
        result = []
        known_techs = self.CATEGORY_TECHNOLOGIES.get(category_lower, frozenset())

        for fact in facts:
            md = fact.metadata or {}
            fact_category = (md.get("category") or "").lower()

            # Technologies: check metadata.category directly
            if fact_category == category_lower:
                result.append(fact)
                continue

            # Projects/experience: check if their technologies match category
            if fact.type in ("project", "experience", "experience_project"):
                technologies_csv = md.get("technologies_csv", "")
                technologies_str = md.get("technologies", "")
                all_techs = f"{technologies_csv} {technologies_str}".lower()

                # Check if any known tech from this category is in project's techs
                if known_techs and any(tech in all_techs for tech in known_techs):
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
