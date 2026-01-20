"""
Acceptance tests for TZ v3 - RAG Agent Hardening.

Tests cover:
1. Normalizer - deterministic fact filtering
2. FactBundle - entity extraction for answer generation

NOTE: Off-topic rejection is handled by scope_guard node.
GroundingVerifier was removed in the 2-LLM architecture simplification.

Based on TZ section 11 acceptance cases:
- "расскажи сказку" → scope_guard rejects
- "какие БД использовал" → only actual DBs from data
- "какие языки программирования" → only category=language
- "чем занимался в АЛОР" → experience/responsibilities
- "где применял RAG" → projects with RAG usage
"""
from __future__ import annotations

import pytest

from app.agent.normalizer.normalizer import FactNormalizer
from app.agent.normalizer.fact_bundle import build_fact_bundle
from app.agent.planner.schemas import FactItem
from app.agent.planner.schemas_v3 import (
    FactBundle,
    FactBundleItem,
    TechCategory,
    TechFilter,
)


class TestNormalizer:
    """Tests for FactNormalizer - deterministic fact filtering."""

    def setup_method(self):
        self.normalizer = FactNormalizer()

    def _make_facts(self, items: list[dict]) -> list[FactItem]:
        """Helper to create FactItem list."""
        return [
            FactItem(
                type=item.get("type", "technology"),
                text=item.get("text", ""),
                metadata=item.get("metadata", {}),
                source_id=item.get("source_id"),
            )
            for item in items
        ]

    def test_technology_overview_filters_by_category(self):
        """technology_overview + category=database should filter to databases only."""
        facts = self._make_facts([
            {"type": "technology", "text": "PostgreSQL", "metadata": {"category": "database"}},
            {"type": "technology", "text": "Python", "metadata": {"category": "language"}},
            {"type": "technology", "text": "MySQL", "metadata": {"category": "database"}},
            {"type": "technology", "text": "FastAPI", "metadata": {"category": "framework"}},
        ])

        tech_filter = TechFilter(category=TechCategory.DATABASE, strict=True)
        result = self.normalizer.normalize(
            facts=facts,
            intent="technology_overview",
            tech_filter=tech_filter,
            max_items=10,
        )

        # Should only have database technologies
        assert len(result.filtered_facts) == 2
        for fact in result.filtered_facts:
            assert fact.metadata.get("category") == "database"

    def test_technology_overview_filters_languages(self):
        """technology_overview + category=language should filter to languages only."""
        facts = self._make_facts([
            {"type": "technology", "text": "Python", "metadata": {"category": "language"}},
            {"type": "technology", "text": "JavaScript", "metadata": {"category": "language"}},
            {"type": "technology", "text": "PostgreSQL", "metadata": {"category": "database"}},
        ])

        tech_filter = TechFilter(category=TechCategory.LANGUAGE, strict=True)
        result = self.normalizer.normalize(
            facts=facts,
            intent="technology_overview",
            tech_filter=tech_filter,
            max_items=10,
        )

        # Should only have language technologies
        assert len(result.filtered_facts) == 2
        for fact in result.filtered_facts:
            assert fact.metadata.get("category") == "language"

    def test_technology_usage_filters_to_tech_facts(self):
        """technology_usage intent should prioritize tech-related facts."""
        facts = self._make_facts([
            {"type": "technology_usage", "text": "Python использовался в RAG"},
            {"type": "technology", "text": "Python"},
            {"type": "project", "text": "AI-Portfolio project"},
            {"type": "achievement", "text": "Increased performance"},
        ])

        result = self.normalizer.normalize(
            facts=facts,
            intent="technology_usage",
            max_items=10,
        )

        # Should filter to technology-related facts
        tech_types = [f.type for f in result.filtered_facts]
        assert "technology_usage" in tech_types or "technology" in tech_types

    def test_experience_summary_prioritizes_experience(self):
        """experience_summary should prioritize experience facts."""
        facts = self._make_facts([
            {"type": "technology", "text": "Python"},
            {"type": "experience", "text": "5 years of experience"},
            {"type": "project", "text": "Built RAG system"},
            {"type": "experience_project", "text": "Developed trading system"},
        ])

        result = self.normalizer.normalize(
            facts=facts,
            intent="experience_summary",
            max_items=10,
        )

        # Experience facts should be first
        if result.filtered_facts:
            first_types = [f.type for f in result.filtered_facts[:2]]
            assert any(t in ["experience", "experience_project"] for t in first_types)

    def test_max_items_limit_applied(self):
        """Max items limit should be respected."""
        facts = self._make_facts([
            {"type": "technology", "text": f"Tech {i}", "metadata": {"category": "language"}}
            for i in range(20)
        ])

        result = self.normalizer.normalize(
            facts=facts,
            intent="technology_overview",
            max_items=5,
        )

        assert len(result.filtered_facts) <= 5

    def test_empty_facts_handled(self):
        """Empty facts list should return empty result."""
        result = self.normalizer.normalize(
            facts=[],
            intent="technology_overview",
            max_items=10,
        )

        assert len(result.filtered_facts) == 0
        assert result.removed_count == 0

    def test_rules_applied_tracked(self):
        """Applied rules should be tracked."""
        facts = self._make_facts([
            {"type": "technology", "text": "PostgreSQL", "metadata": {"category": "database"}},
        ])

        tech_filter = TechFilter(category=TechCategory.DATABASE, strict=True)
        result = self.normalizer.normalize(
            facts=facts,
            intent="technology_overview",
            tech_filter=tech_filter,
            max_items=10,
        )

        assert len(result.rules_applied) > 0


class TestFactBundle:
    """Tests for FactBundle building and entity extraction."""

    def _make_facts(self, items: list[dict]) -> list[FactItem]:
        """Helper to create FactItem list."""
        return [
            FactItem(
                type=item.get("type", "technology"),
                text=item.get("text", ""),
                metadata=item.get("metadata", {}),
                source_id=item.get("source_id"),
            )
            for item in items
        ]

    def test_extracts_technologies_from_metadata(self):
        """Should extract technologies from metadata."""
        facts = self._make_facts([
            {"type": "technology", "text": "Python programming", "metadata": {"name": "Python"}},
            {"type": "technology", "text": "PostgreSQL database", "metadata": {"name": "PostgreSQL"}},
        ])

        bundle = build_fact_bundle(facts)

        assert "Python" in bundle.technologies
        assert "PostgreSQL" in bundle.technologies

    def test_extracts_companies(self):
        """Should extract companies from metadata."""
        facts = self._make_facts([
            {"type": "experience", "text": "Worked at ALOR", "metadata": {"company_name": "ALOR"}},
        ])

        bundle = build_fact_bundle(facts)

        assert "ALOR" in bundle.companies

    def test_extracts_projects(self):
        """Should extract projects from metadata."""
        facts = self._make_facts([
            {"type": "project", "text": "AI-Portfolio project", "metadata": {"name": "AI-Portfolio"}},
        ])

        bundle = build_fact_bundle(facts)

        assert "AI-Portfolio" in bundle.projects

    def test_extracts_technologies_list(self):
        """Should extract technologies from list in metadata."""
        facts = self._make_facts([
            {
                "type": "project",
                "text": "Project with tech stack",
                "metadata": {"technologies": ["Python", "FastAPI", "PostgreSQL"]},
            },
        ])

        bundle = build_fact_bundle(facts)

        assert "Python" in bundle.technologies
        assert "FastAPI" in bundle.technologies
        assert "PostgreSQL" in bundle.technologies

    def test_empty_facts_returns_empty_bundle(self):
        """Empty facts should return empty bundle."""
        bundle = build_fact_bundle([])

        assert len(bundle.facts) == 0
        assert len(bundle.technologies) == 0
        assert len(bundle.companies) == 0
        assert len(bundle.projects) == 0


class TestIntegration:
    """Integration tests for the full pipeline components."""

    def test_normalizer_to_fact_bundle_flow(self):
        """Test that normalized facts can be bundled correctly."""
        normalizer = FactNormalizer()

        facts = [
            FactItem(
                type="technology",
                text="Python - основной язык",
                metadata={"name": "Python", "category": "language"},
            ),
            FactItem(
                type="technology",
                text="PostgreSQL - база данных",
                metadata={"name": "PostgreSQL", "category": "database"},
            ),
        ]

        # Filter to languages only
        tech_filter = TechFilter(category=TechCategory.LANGUAGE, strict=True)
        normalized = normalizer.normalize(
            facts=facts,
            intent="technology_overview",
            tech_filter=tech_filter,
            max_items=10,
        )

        # Build bundle from filtered facts
        filtered_fact_items = [
            FactItem(
                type=f.type,
                text=f.text,
                metadata=f.metadata or {},
                source_id=f.entity_id,
            )
            for f in normalized.filtered_facts
        ]
        bundle = build_fact_bundle(filtered_fact_items)

        # Should only have Python
        assert "Python" in bundle.technologies
        assert "PostgreSQL" not in bundle.technologies
