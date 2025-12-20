"""
Render Engine - deterministic rendering of facts to formatted text.

Supports multiple render styles: BULLETS, GROUPED_BULLETS, SHORT, TABLE.
Based on ТЗ section 8.
"""
from __future__ import annotations

import re
from typing import Any

from ..planner.schemas import FactItem, RenderStyle, IntentV2


class RenderEngine:
    """
    Deterministic rendering of facts to formatted text.

    Renders FactItem lists to markdown-formatted strings
    based on render_style.
    """

    def render(
        self,
        facts: list[FactItem],
        style: RenderStyle,
        intents: list[IntentV2],
        max_items: int = 10,
    ) -> str:
        """
        Render facts to formatted text.

        Args:
            facts: List of facts to render
            style: Render style (BULLETS, GROUPED_BULLETS, SHORT, TABLE)
            intents: Detected intents for context-aware rendering
            max_items: Maximum items to render

        Returns:
            Formatted markdown string
        """
        if not facts:
            return ""

        # Limit facts
        limited_facts = facts[:max_items]

        if style == RenderStyle.BULLETS:
            return self._render_bullets(limited_facts)
        elif style == RenderStyle.GROUPED_BULLETS:
            return self._render_grouped_bullets(limited_facts)
        elif style == RenderStyle.SHORT:
            return self._render_short(limited_facts)
        elif style == RenderStyle.TABLE:
            return self._render_table(limited_facts, intents)

        # Default to bullets
        return self._render_bullets(limited_facts)

    def _render_bullets(self, facts: list[FactItem]) -> str:
        """Render facts as bulleted list."""
        lines = []
        for fact in facts:
            text = self._clean_text(fact.text)
            if text:
                lines.append(f"- {text}")
        return "\n".join(lines)

    def _render_grouped_bullets(self, facts: list[FactItem]) -> str:
        """Render facts grouped by type."""
        # Group by type
        groups: dict[str, list[str]] = {}
        for fact in facts:
            key = self._get_group_title(fact.type)
            if key not in groups:
                groups[key] = []
            text = self._clean_text(fact.text)
            if text:
                groups[key].append(text)

        # Render groups
        lines = []
        for group_name, items in groups.items():
            if items:
                lines.append(f"\n**{group_name}:**")
                for item in items:
                    lines.append(f"- {item}")

        return "\n".join(lines).strip()

    def _render_short(self, facts: list[FactItem]) -> str:
        """Render first 2-3 facts as short paragraph."""
        texts = []
        for fact in facts[:3]:
            text = self._clean_text(fact.text)
            if text:
                texts.append(text)
        return " ".join(texts)

    def _render_table(self, facts: list[FactItem], intents: list[IntentV2]) -> str:
        """Render as markdown table."""
        if not facts:
            return ""

        # Determine table format based on intent
        if IntentV2.CONTACTS in intents:
            return self._table_contacts(facts)
        elif IntentV2.TECHNOLOGY_OVERVIEW in intents:
            return self._table_technologies(facts)
        elif IntentV2.PROJECT_TECH_STACK in intents:
            return self._table_technologies(facts)

        # Generic table
        lines = ["| Элемент | Описание |", "|---------|----------|"]
        for fact in facts:
            text = self._clean_text(fact.text)[:100]  # Truncate for table
            lines.append(f"| {fact.type} | {text} |")
        return "\n".join(lines)

    def _table_contacts(self, facts: list[FactItem]) -> str:
        """Render contacts as table."""
        lines = ["| Тип | Контакт |", "|-----|---------|"]
        for fact in facts:
            kind = fact.metadata.get("kind", fact.type)
            value = (
                fact.metadata.get("url")
                or fact.metadata.get("value")
                or fact.text
            )
            lines.append(f"| {kind} | {value} |")
        return "\n".join(lines)

    def _table_technologies(self, facts: list[FactItem]) -> str:
        """Render technologies as table."""
        lines = ["| Технология | Категория |", "|------------|-----------|"]
        for fact in facts:
            name = fact.metadata.get("name", fact.text)
            category = fact.metadata.get("category", "-")
            lines.append(f"| {name} | {category} |")
        return "\n".join(lines)

    def _clean_text(self, text: str) -> str:
        """Clean text for rendering."""
        if not text:
            return ""

        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove existing bullet if present
        if text.startswith("- "):
            text = text[2:]

        # Remove multiple spaces
        text = re.sub(r" {2,}", " ", text)

        return text

    def _get_group_title(self, fact_type: str) -> str:
        """Get human-readable group title."""
        titles = {
            "achievement": "Достижения",
            "technology": "Технологии",
            "project": "Проекты",
            "experience": "Опыт",
            "contact": "Контакты",
            "text": "Информация",
            "document": "Документы",
        }
        return titles.get(fact_type, fact_type.title())


# === Post-processing utilities ===

# Forbidden phrases that should be removed from answers
FORBIDDEN_PHRASES = [
    "согласно предоставленным данным",
    "на основе имеющихся данных",
    "в предоставленном контексте",
    "судя по информации",
    "рекомендуется уточнить",
    "конфиденциальность",
    "конкретных упоминаний не найдено",
    "других данных нет",
    "больше информации не обнаружено",
    "according to the data",
    "based on the provided",
]

# Patterns for technical artifacts
ARTIFACT_PATTERNS = [
    re.compile(r"\[\d+\]"),  # Reference markers [1], [2]
    re.compile(r"confidence[:\s]*[\d.]+", re.IGNORECASE),  # Confidence scores
    re.compile(r"source[:\s]*\w+", re.IGNORECASE),  # Source mentions
    re.compile(r"\{[^}]*\}"),  # JSON fragments
    re.compile(r"metadata[:\s]*", re.IGNORECASE),  # Metadata mentions
]


def post_process_answer(answer: str) -> tuple[str, list[str]]:
    """
    Post-process answer to remove artifacts.

    Args:
        answer: Raw answer text

    Returns:
        Tuple of (cleaned_answer, warnings)
    """
    warnings = []
    cleaned = answer

    # Remove forbidden phrases
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in cleaned.lower():
            warnings.append(f"Removed forbidden phrase: {phrase[:20]}...")
            cleaned = re.sub(
                re.escape(phrase),
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

    # Remove artifact patterns
    for pattern in ARTIFACT_PATTERNS:
        if pattern.search(cleaned):
            warnings.append(f"Removed artifact pattern")
            cleaned = pattern.sub("", cleaned)

    # Clean up whitespace
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip(), warnings
