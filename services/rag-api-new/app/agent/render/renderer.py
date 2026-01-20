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

        # Special handling for PROJECT_LIST intent
        # Add project summary and render technology facts in project-centric way
        # Check both IntentV2 and IntentV3 (or string values) for compatibility
        if intents and self._has_intent(intents, "project_list"):
            return self._render_project_list(limited_facts)

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

    def _render_project_list(self, facts: list[FactItem]) -> str:
        """
        Render facts for PROJECT_LIST intent with project summary.

        This ensures all projects are explicitly listed, even those
        mentioned only in technology facts.
        """
        # Step 1: Extract all unique projects from all facts
        all_projects = self._extract_all_projects(facts)

        # Step 2: Build output with project summary first
        lines = []

        # Add project summary if we found multiple projects
        if len(all_projects) > 1:
            project_list = ", ".join(sorted(all_projects))
            lines.append(f"[Проекты в контексте: {project_list}]")
            lines.append("ВАЖНО: Упомяни ВСЕ проекты из списка выше в ответе.")
            lines.append("")

        # Step 3: Render direct project facts (experience_project, project)
        project_facts = [f for f in facts if f.type in ("project", "experience_project")]
        for fact in project_facts:
            text = self._clean_text(fact.text)
            if text:
                # Keep full project description
                lines.append(f"[Проект] {text}")
                lines.append("")

        # Step 4: Render technology facts in project-centric way
        tech_facts = [f for f in facts if f.type == "technology"]
        if tech_facts:
            # Extract projects from technology facts that aren't already covered
            covered_projects = set()
            for f in project_facts:
                md = f.metadata or {}
                name = md.get("name") or md.get("project_name")
                if name:
                    covered_projects.add(name)

            # Render technology facts emphasizing projects
            tech_projects_info = []
            for fact in tech_facts:
                md = fact.metadata or {}
                tech_name = md.get("name") or md.get("slug", "")
                project_names_csv = md.get("project_names_csv") or ""

                if project_names_csv and tech_name:
                    projects = [p.strip() for p in project_names_csv.split(",")]
                    # Find projects not yet covered
                    new_projects = [p for p in projects if p not in covered_projects]
                    if new_projects:
                        tech_projects_info.append(
                            f"- {tech_name} используется в: {', '.join(projects)}"
                        )
                        covered_projects.update(projects)

            if tech_projects_info:
                lines.append("[Технологии и связанные проекты]")
                lines.extend(tech_projects_info)
                lines.append("")

        # Step 5: Render experience facts (company-level)
        exp_facts = [f for f in facts if f.type == "experience"]
        for fact in exp_facts:
            text = self._clean_text(fact.text)
            if text and len(text) < 500:  # Only short summaries
                lines.append(f"[Опыт] {text}")

        return "\n".join(lines).strip()

    def _extract_all_projects(self, facts: list[FactItem]) -> set[str]:
        """
        Extract all unique project names from facts.

        Looks in:
        - Direct project facts (name from metadata)
        - Technology facts (project_names_csv in metadata)

        NOTE: Uses only human-readable names, not slugs.
        """
        projects = set()

        for fact in facts:
            md = fact.metadata or {}

            # From project/experience_project facts - use name only
            if fact.type in ("project", "experience_project"):
                name = md.get("name") or md.get("project_name")
                if name:
                    projects.add(name)

            # From technology facts - extract from project_names_csv (contains names, not slugs)
            if fact.type == "technology":
                project_names_csv = md.get("project_names_csv") or ""
                if project_names_csv:
                    for p in project_names_csv.split(","):
                        p = p.strip()
                        if p:
                            projects.add(p)

            # From experience facts - use project names from text parsing
            # Skip project_slugs_csv as it contains slugs, not names
            if fact.type == "experience":
                # Check if there's a "Проекты:" line in the text
                if "Проекты:" in fact.text:
                    # Extract project names after "Проекты:"
                    parts = fact.text.split("Проекты:")
                    if len(parts) > 1:
                        project_part = parts[1].strip().split("\n")[0]
                        for p in project_part.split(","):
                            p = p.strip()
                            if p:
                                projects.add(p)

        return projects

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

    def _has_intent(self, intents: list, intent_value: str) -> bool:
        """
        Check if intents list contains a specific intent.

        Works with both IntentV2, IntentV3 enums and string values.
        """
        for intent in intents:
            # Handle enum objects (IntentV2, IntentV3)
            if hasattr(intent, "value"):
                if intent.value == intent_value:
                    return True
            # Handle string values
            elif isinstance(intent, str):
                if intent == intent_value:
                    return True
        return False

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
    "не описана подробно",
    "не описан подробно",
    "не указан подробный контекст",
    "не указан контекст использования",
    "контекст использования не найден",
    "не найдено подробной информации",
    "информации недостаточно",
    "к сожалению, информации",
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

# Patterns for sentences that should be REMOVED entirely
# (entire sentence containing these patterns will be removed)
SENTENCE_REMOVAL_PATTERNS = [
    # "X: на этом проекте технология Y не описана подробно."
    re.compile(r"[^.!?]*(?:не описан|не найден|не указан)[^.!?]*(?:подробно|контекст)[^.!?]*[.!?]", re.IGNORECASE),
    # "Технология X не упоминается подробно в проекте Y."
    re.compile(r"[^.!?]*(?:не упоминается|не применя)[^.!?]*подробно[^.!?]*[.!?]", re.IGNORECASE),
]


def post_process_answer(answer: str) -> tuple[str, list[str]]:
    """
    Post-process answer to remove artifacts and forbidden phrases.

    SYSTEMIC SOLUTION: Removes not just phrases, but entire sentences
    containing patterns like "X не описана подробно", "не найден контекст".

    Args:
        answer: Raw answer text

    Returns:
        Tuple of (cleaned_answer, warnings)
    """
    warnings = []
    cleaned = answer

    # 1. Remove entire sentences matching removal patterns
    # This handles "F3 TAIL: на этом проекте технология RAG не описана подробно."
    for pattern in SENTENCE_REMOVAL_PATTERNS:
        matches = pattern.findall(cleaned)
        if matches:
            for match in matches:
                warnings.append(f"Removed sentence: {match[:50]}...")
            cleaned = pattern.sub("", cleaned)

    # 2. Remove forbidden phrases
    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in cleaned.lower():
            warnings.append(f"Removed forbidden phrase: {phrase[:20]}...")
            cleaned = re.sub(
                re.escape(phrase),
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

    # 3. Remove artifact patterns
    for pattern in ARTIFACT_PATTERNS:
        if pattern.search(cleaned):
            warnings.append(f"Removed artifact pattern")
            cleaned = pattern.sub("", cleaned)

    # 4. Clean up: remove empty list items like "- " or bullet points with just whitespace
    cleaned = re.sub(r"^-\s*$", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n-\s*\n", "\n", cleaned)

    # 5. Clean up whitespace
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned.strip(), warnings
