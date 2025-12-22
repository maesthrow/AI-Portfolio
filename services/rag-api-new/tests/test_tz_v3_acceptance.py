"""
Acceptance tests for TZ v3 - RAG Agent Hardening.

Tests cover:
1. GroundingVerifier - hallucination detection
2. Normalizer - deterministic fact filtering
3. FactBundle - entity extraction for grounding

NOTE: Off-topic rejection is now handled by agent's system prompt (see graph.py).
Agent decides whether to call portfolio_rag_tool or respond directly.
ScopeGuard module is no longer used in the main pipeline.

Based on TZ section 11 acceptance cases:
- "расскажи сказку" → agent refuses without calling tool
- "какие БД использовал" → only actual DBs from data
- "какие языки программирования" → only category=language
- "чем занимался в АЛОР" → experience/responsibilities
- "где применял RAG" → projects with RAG usage
"""
from __future__ import annotations

import pytest

from app.agent.grounding.grounding_verifier import GroundingVerifier
from app.agent.normalizer.normalizer import FactNormalizer
from app.agent.normalizer.fact_bundle import build_fact_bundle
from app.agent.planner.schemas import FactItem
from app.agent.planner.schemas_v3 import (
    FactBundle,
    FactBundleItem,
    TechCategory,
    TechFilter,
    GroundingResult,
)


class TestGroundingVerifier:
    """Tests for GroundingVerifier - hallucination detection."""

    def setup_method(self):
        self.verifier = GroundingVerifier()

    def _make_fact_bundle(
        self,
        technologies: list[str] | None = None,
        companies: list[str] | None = None,
        projects: list[str] | None = None,
    ) -> FactBundle:
        """Helper to create a FactBundle for testing."""
        return FactBundle(
            facts=[],
            technologies=technologies or [],
            companies=companies or [],
            projects=projects or [],
            roles=[],
            dates=[],
        )

    def test_grounded_answer_accepted(self):
        """Answer with only known entities should be accepted."""
        bundle = self._make_fact_bundle(
            technologies=["Python", "PostgreSQL", "FastAPI"],
            companies=["ALOR"],
        )

        answer = "Использую Python и PostgreSQL для разработки в ALOR."
        result = self.verifier.verify(answer, bundle)

        assert result.grounded is True
        assert result.action == "accept"

    def test_hallucinated_technology_detected(self):
        """Answer mentioning unknown technology should be flagged."""
        bundle = self._make_fact_bundle(
            technologies=["Python", "PostgreSQL"],
        )

        # MySQL not in bundle
        answer = "Использую MySQL и MongoDB для хранения данных."
        result = self.verifier.verify(answer, bundle)

        # Should detect MySQL/MongoDB as ungrounded
        assert result.grounded is False
        assert len(result.ungrounded_entities) > 0

    def test_speculation_markers_detected(self):
        """Speculation markers like 'вероятно' should trigger rewrite."""
        bundle = self._make_fact_bundle(technologies=["Python"])

        answer = "Вероятно использовал Python для разработки."
        result = self.verifier.verify(answer, bundle)

        assert result.grounded is False
        assert "вероятно" in [u.lower() for u in result.ungrounded_entities]
        assert result.action == "rewrite"

    def test_speculation_maybe_detected(self):
        """English speculation 'maybe' should be detected."""
        bundle = self._make_fact_bundle(technologies=["Python"])

        answer = "Maybe used Python for the project."
        result = self.verifier.verify(answer, bundle)

        assert result.grounded is False
        assert result.action == "rewrite"

    def test_empty_answer_accepted(self):
        """Empty answer should be accepted."""
        bundle = self._make_fact_bundle()
        result = self.verifier.verify("", bundle)

        assert result.grounded is True

    def test_camelcase_technology_matched(self):
        """CamelCase technologies should be matched."""
        bundle = self._make_fact_bundle(
            technologies=["FastAPI", "LangChain", "PostgreSQL"],
        )

        answer = "Разработка на FastAPI с использованием LangChain."
        result = self.verifier.verify(answer, bundle)

        assert result.grounded is True

    def test_fuzzy_match_works(self):
        """Partial matches like 'postgres' for 'PostgreSQL' should work."""
        bundle = self._make_fact_bundle(
            technologies=["PostgreSQL"],
        )

        # 'postgres' should match 'PostgreSQL'
        answer = "Использую postgres для хранения данных."
        result = self.verifier.verify(answer, bundle)

        assert result.grounded is True

    def test_many_ungrounded_triggers_refuse(self):
        """Too many ungrounded entities should trigger refuse."""
        bundle = self._make_fact_bundle(technologies=["Python"])

        # Many unknown technologies
        answer = "Использую MySQL, MongoDB, Redis, Elasticsearch и Cassandra."
        result = self.verifier.verify(answer, bundle)

        assert result.grounded is False
        # With 5 unknown entities, should refuse
        assert result.action == "refuse"

    def test_suggested_rewrite_removes_ungrounded(self):
        """Suggested rewrite should not contain ungrounded entities."""
        bundle = self._make_fact_bundle(
            technologies=["Python", "PostgreSQL"],
        )

        answer = "Использую Python и PostgreSQL. Также работал с MySQL и Redis."
        result = self.verifier.verify(answer, bundle)

        if result.action == "rewrite" and result.suggested_rewrite:
            # MySQL and Redis should not be in rewritten text
            assert "MySQL" not in result.suggested_rewrite
            assert "Redis" not in result.suggested_rewrite


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
