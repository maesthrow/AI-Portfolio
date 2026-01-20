"""
Tool schemas for the new specialized tools.

Defines ToolResult dataclass used by all tools for consistent return format.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..planner.schemas import FactItem


@dataclass
class ToolResult:
    """
    Standard result from any tool execution.

    All specialized tools (get_company_projects, get_project_details,
    get_technologies, search_portfolio) return this format.

    Attributes:
        facts: List of extracted facts
        sources: List of source references
        found: Whether any results were found
        confidence: Confidence score (0.0-1.0)
        tool_name: Name of the tool that produced this result
        params: Parameters used for the tool call
        evidence_text: Optional rendered evidence text
        error: Optional error message if tool failed
    """
    facts: list[FactItem] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    found: bool = False
    confidence: float = 0.0
    tool_name: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    evidence_text: str = ""
    error: str | None = None

    def __bool__(self) -> bool:
        """Return True if tool found results."""
        return self.found and len(self.facts) > 0

    def merge(self, other: "ToolResult") -> "ToolResult":
        """Merge another ToolResult into this one."""
        if not other:
            return self

        # Deduplicate facts by source_id
        existing_ids = {f.source_id for f in self.facts if f.source_id}
        new_facts = [
            f for f in other.facts
            if not f.source_id or f.source_id not in existing_ids
        ]

        return ToolResult(
            facts=self.facts + new_facts,
            sources=self.sources + other.sources,
            found=self.found or other.found,
            confidence=max(self.confidence, other.confidence),
            tool_name=self.tool_name or other.tool_name,
            params={**self.params, **other.params},
            evidence_text=(self.evidence_text + "\n\n" + other.evidence_text).strip(),
            error=self.error or other.error,
        )


# Tool names for registry
TOOL_GET_COMPANY_PROJECTS = "get_company_projects"
TOOL_GET_PROJECT_DETAILS = "get_project_details"
TOOL_GET_TECHNOLOGIES = "get_technologies"
TOOL_GET_CONTACTS = "get_contacts"
TOOL_SEARCH_PORTFOLIO = "search_portfolio"

# New tools for improved quality (ТЗ v3)
TOOL_GET_WORK_HISTORY = "get_work_history"
TOOL_GET_COMPANY_ACHIEVEMENTS = "get_company_achievements"
TOOL_GET_PROJECT_ACHIEVEMENTS = "get_project_achievements"
TOOL_GET_PROJECT_SUMMARY = "get_project_summary"
TOOL_GET_COMPANY_SUMMARY = "get_company_summary"

# All available tools
ALL_TOOLS = [
    TOOL_GET_COMPANY_PROJECTS,
    TOOL_GET_PROJECT_DETAILS,
    TOOL_GET_TECHNOLOGIES,
    TOOL_GET_CONTACTS,
    TOOL_SEARCH_PORTFOLIO,
    # New tools (ТЗ v3)
    TOOL_GET_WORK_HISTORY,
    TOOL_GET_COMPANY_ACHIEVEMENTS,
    TOOL_GET_PROJECT_ACHIEVEMENTS,
    TOOL_GET_PROJECT_SUMMARY,
    TOOL_GET_COMPANY_SUMMARY,
]
