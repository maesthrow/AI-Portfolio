"""
Response Formatter - Epic 3.

Transforms SearchResult to natural, user-friendly text.
Removes technical artifacts and applies consistent formatting.
"""
from __future__ import annotations

import re
from typing import Any, List

from .search_types import Intent


# === Patterns for post-processing ===

REFERENCE_PATTERN = re.compile(r'\[\d+\]')  # [1], [2], etc.
CONFIDENCE_PATTERN = re.compile(r'confidence[:\s]*[\d.]+', re.IGNORECASE)

TAIL_PATTERNS = [
    re.compile(r'конкретных упоминаний.*?не найдено', re.IGNORECASE),
    re.compile(r'других данных.*?нет', re.IGNORECASE),
    re.compile(r'больше информации.*?не обнаружено', re.IGNORECASE),
    re.compile(r'дополнительной информации.*?нет', re.IGNORECASE),
    re.compile(r'других упоминаний.*?нет', re.IGNORECASE),
]


class FormatRenderer:
    """
    Renders items and post-processes LLM answers.

    Handles:
    - Converting structured items to bulleted lists
    - Removing technical artifacts ([1], [2], confidence)
    - Removing "tail" phrases about missing data
    """

    def __init__(self, style_hint: str | None = None):
        self.style_hint = style_hint

    def render_items(self, items: List[Any], intent: Intent) -> str:
        """
        Render structured items based on intent and style.

        Args:
            items: List of item dictionaries
            intent: Query intent for format selection

        Returns:
            Formatted string with bulleted list
        """
        if intent == Intent.ACHIEVEMENTS:
            return self.render_achievements(items)
        elif intent == Intent.TECHNOLOGIES:
            return self.render_technologies(items)
        elif intent == Intent.CONTACTS:
            return self.render_contacts(items)
        elif intent == Intent.LANGUAGES:
            return self.render_languages(items)
        elif intent == Intent.EXPERIENCE:
            return self.render_experience(items)
        elif intent == Intent.PROJECT_DETAILS:
            return self.render_project(items)

        # Generic fallback
        return self._to_list_format([str(item) for item in items])

    def render_achievements(self, items: List[dict]) -> str:
        """Render achievements as bulleted list."""
        lines = []
        for item in items:
            text = item.get("text") or item.get("achievement") or str(item)
            if text and text.strip():
                lines.append(text.strip())
        return self._to_list_format(lines)

    def render_technologies(self, items: List[dict]) -> str:
        """Render technologies as bulleted list."""
        names = []
        for item in items:
            name = item.get("name") or item.get("slug") or str(item)
            if name and name.strip():
                names.append(name.strip())
        return self._to_list_format(names)

    def render_languages(self, items: List[dict]) -> str:
        """Render programming languages as bulleted list."""
        names = []
        for item in items:
            name = item.get("name") or item.get("slug") or str(item)
            if name and name.strip():
                names.append(name.strip())
        return self._to_list_format(names)

    def render_contacts(self, items: List[dict]) -> str:
        """Render contacts with type and value."""
        lines = []
        for item in items:
            kind = item.get("kind") or item.get("type") or ""
            value = item.get("value") or ""
            url = item.get("url") or ""
            if url:
                lines.append(f"{kind}: {url}")
            elif value:
                lines.append(f"{kind}: {value}")
        return self._to_list_format(lines)

    def render_experience(self, items: List[dict]) -> str:
        """Render work experience entries."""
        lines = []
        for item in items:
            company = item.get("company") or item.get("company_name") or ""
            role = item.get("role") or item.get("position") or ""
            period = item.get("period") or ""
            if company and role:
                line = f"{company} — {role}"
                if period:
                    line += f" ({period})"
                lines.append(line)
            elif company:
                lines.append(company)
        return self._to_list_format(lines)

    def render_project(self, items: List[dict]) -> str:
        """Render project details."""
        if not items:
            return ""

        lines = []
        for item in items:
            name = item.get("name") or item.get("title") or ""
            desc = item.get("description") or item.get("text") or ""
            if name:
                lines.append(name)
            if desc:
                lines.append(desc)
        return "\n".join(lines)

    def post_process(self, answer: str, found: bool = True) -> str:
        """
        Remove technical artifacts from LLM answer.

        Args:
            answer: Raw LLM output
            found: Whether data was found (affects tail removal)

        Returns:
            Cleaned answer string
        """
        result = self._remove_references(answer)
        result = self._remove_confidence(result)
        result = self._remove_tail_phrases(result)
        result = self._cleanup_whitespace(result)
        return result.strip()

    def _remove_references(self, text: str) -> str:
        """Remove [1], [2] style references."""
        return REFERENCE_PATTERN.sub('', text)

    def _remove_confidence(self, text: str) -> str:
        """Remove confidence mentions like 'confidence: 0.85'."""
        return CONFIDENCE_PATTERN.sub('', text)

    def _remove_tail_phrases(self, text: str) -> str:
        """Remove phrases about missing data."""
        for pattern in TAIL_PATTERNS:
            text = pattern.sub('', text)
        return text

    def _cleanup_whitespace(self, text: str) -> str:
        """Clean up multiple spaces and empty lines."""
        # Replace multiple spaces with single
        text = re.sub(r' {2,}', ' ', text)
        # Replace multiple newlines with double
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    def _to_list_format(self, items: List[str]) -> str:
        """Convert items to bulleted list format."""
        result = []
        for item in items:
            if item and item.strip():
                clean = item.strip()
                # Remove existing bullet if present
                if clean.startswith('- '):
                    clean = clean[2:]
                result.append(f'- {clean}')
        return '\n'.join(result)


# === Not Found Responses ===

_NOT_FOUND_RESPONSES: dict[Intent, str] = {
    Intent.ACHIEVEMENTS: "У меня нет информации о достижениях по этому запросу.",
    Intent.TECHNOLOGIES: "Такой технологии в моём портфолио нет.",
    Intent.CONTACTS: "Такой контактной информации у меня нет.",
    Intent.PROJECT_DETAILS: "Такого проекта в портфолио не нашлось.",
    Intent.CURRENT_JOB: "Информации о текущем месте работы нет в портфолио.",
    Intent.EXPERIENCE: "Такого опыта работы в портфолио нет.",
    Intent.LANGUAGES: "Информации об этом языке программирования нет.",
    Intent.GENERAL: "Такой информации в портфолио нет.",
}


def format_not_found_response(intent: Intent) -> str:
    """
    Generate short 'not found' response without listing what's missing.

    Args:
        intent: Query intent for response selection

    Returns:
        Short, user-friendly "not found" message
    """
    return _NOT_FOUND_RESPONSES.get(intent, "Такой информации нет в портфолио.")
