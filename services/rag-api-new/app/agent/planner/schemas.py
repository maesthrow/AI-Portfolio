"""
Pydantic schemas for LLM-based query planning.

Contains all data structures for the Planner LLM -> Executor -> Answer LLM pipeline.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntentV2(str, Enum):
    """
    Extended intents for LLM-based planning.

    Based on ТЗ section 6.2 - minimal set of intents.
    """
    CURRENT_JOB = "current_job"
    PROJECT_DETAILS = "project_details"
    PROJECT_ACHIEVEMENTS = "project_achievements"
    PROJECT_TECH_STACK = "project_tech_stack"
    TECHNOLOGY_USAGE = "technology_usage"
    EXPERIENCE_SUMMARY = "experience_summary"
    TECHNOLOGY_OVERVIEW = "technology_overview"
    CONTACTS = "contacts"
    GENERAL_UNSTRUCTURED = "general_unstructured"


class RenderStyle(str, Enum):
    """
    Deterministic rendering styles for answer formatting.

    Based on ТЗ section 8.1.
    """
    BULLETS = "bullets"
    GROUPED_BULLETS = "grouped_bullets"
    SHORT = "short"
    TABLE = "table"


class AnswerStyle(str, Enum):
    """Style hints for Answer LLM generation."""
    NATURAL_RU = "natural_ru"
    CONCISE = "concise"
    DETAILED = "detailed"
    ENUMERATION = "enumeration"


class EntityV2(BaseModel):
    """
    Extracted entity from user question.

    Planner LLM identifies entities and maps them to canonical IDs.
    """
    type: str = Field(description="Entity type: project, company, technology, person")
    id: str = Field(description="Canonical entity ID, e.g., 'project:alor-broker'")
    name: str = Field(description="Human-readable entity name")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "project",
                "id": "project:alor-broker",
                "name": "ALOR Broker",
                "confidence": 0.9
            }
        }


class ToolCall(BaseModel):
    """
    Single tool invocation specification.

    Planner LLM generates a sequence of ToolCalls to execute.
    """
    tool: str = Field(description="Tool name: graph_query_tool, portfolio_search_tool")
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments (intent, entity_id, query, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tool": "graph_query_tool",
                "args": {"intent": "PROJECT_ACHIEVEMENTS", "entity_id": "project:alor-broker"}
            }
        }


class FallbackConfig(BaseModel):
    """
    Fallback behavior when primary plan fails.

    Based on ТЗ section 6.1 - fallback structure.
    """
    enabled: bool = Field(default=True, description="Whether fallback is enabled")
    tool: str = Field(default="portfolio_search_tool", description="Fallback tool to use")
    when: list[str] = Field(
        default_factory=lambda: ["NO_RESULTS", "LOW_COVERAGE"],
        description="Conditions triggering fallback"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "tool": "portfolio_search_tool",
                "when": ["NO_RESULTS", "LOW_COVERAGE"]
            }
        }


class LimitsConfig(BaseModel):
    """
    Search and rendering limits.

    Based on ТЗ section 6.1 - limits structure.
    """
    max_items: int = Field(default=10, ge=1, le=50, description="Max items to return")
    max_groups: int = Field(default=4, ge=1, le=10, description="Max groups for grouped rendering")
    max_paragraphs: int = Field(default=4, ge=1, le=10, description="Max paragraphs for long answers")

    class Config:
        json_schema_extra = {
            "example": {
                "max_items": 10,
                "max_groups": 4,
                "max_paragraphs": 4
            }
        }


class QueryPlanV2(BaseModel):
    """
    LLM-generated query execution plan.

    Main output of Planner LLM. Contains all information needed
    to execute the query and render the response.

    Based on ТЗ section 6.1 - QueryPlan format.
    """
    intents: list[IntentV2] = Field(
        description="One or more detected intents"
    )
    entities: list[EntityV2] = Field(
        default_factory=list,
        description="Extracted entities with canonical IDs"
    )
    tool_calls: list[ToolCall] = Field(
        description="Sequence of tool invocations"
    )
    fallback: FallbackConfig = Field(
        default_factory=FallbackConfig,
        description="Fallback configuration"
    )
    limits: LimitsConfig = Field(
        default_factory=LimitsConfig,
        description="Search and render limits"
    )
    render_style: RenderStyle = Field(
        default=RenderStyle.BULLETS,
        description="How to format the response"
    )
    answer_style: AnswerStyle = Field(
        default=AnswerStyle.NATURAL_RU,
        description="Tone and style of the answer"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Planner's confidence in the plan"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "intents": ["PROJECT_ACHIEVEMENTS"],
                "entities": [
                    {"type": "project", "id": "project:alor-broker", "name": "ALOR Broker", "confidence": 0.9}
                ],
                "tool_calls": [
                    {"tool": "graph_query_tool", "args": {"intent": "PROJECT_ACHIEVEMENTS", "entity_id": "project:alor-broker"}}
                ],
                "fallback": {"enabled": True, "tool": "portfolio_search_tool", "when": ["NO_RESULTS"]},
                "limits": {"max_items": 10, "max_groups": 4, "max_paragraphs": 4},
                "render_style": "bullets",
                "answer_style": "natural_ru",
                "confidence": 0.86
            }
        }


class FactItem(BaseModel):
    """
    Single fact extracted from tool execution.

    Part of FactsPayload - used by Answer LLM.
    """
    type: str = Field(description="Fact type: achievement, technology, project, contact, etc.")
    text: str = Field(description="Main fact content")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured data"
    )
    source_id: str | None = Field(
        default=None,
        description="Source document/entity ID for traceability"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "achievement",
                "text": "Разработал систему риск-менеджмента для брокера",
                "metadata": {"project": "alor-broker"},
                "source_id": "project:alor-broker"
            }
        }


class SourceInfo(BaseModel):
    """Source reference for facts."""
    id: str
    label: str
    type: str | None = None


class FactsPayload(BaseModel):
    """
    Collection of facts from tool execution.

    Passed to Answer LLM for response generation.
    Based on ТЗ section 7.3 - FactsPayload structure.
    """
    found: bool = Field(default=False, description="Whether any facts were found")
    items: list[FactItem] = Field(
        default_factory=list,
        description="Individual facts"
    )
    groups: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Grouped facts for GROUPED_BULLETS style"
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the search (coverage, etc.)"
    )
    sources: list[SourceInfo] = Field(
        default_factory=list,
        description="Source references"
    )

    # Context for Answer LLM
    query: str = Field(default="", description="Original user question")
    intents: list[IntentV2] = Field(
        default_factory=list,
        description="Detected intents"
    )
    render_style: RenderStyle = Field(
        default=RenderStyle.BULLETS,
        description="Requested render style"
    )
    answer_style: AnswerStyle = Field(
        default=AnswerStyle.NATURAL_RU,
        description="Requested answer style"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings from execution (e.g., fallback used)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "found": True,
                "items": [
                    {"type": "achievement", "text": "Разработал RAG-систему", "metadata": {}, "source_id": "project:ai-portfolio"}
                ],
                "groups": [],
                "meta": {"coverage": 0.9},
                "sources": [{"id": "project:ai-portfolio", "label": "AI-Portfolio", "type": "project"}],
                "query": "Какие достижения в AI-Portfolio?",
                "intents": ["PROJECT_ACHIEVEMENTS"],
                "render_style": "bullets",
                "answer_style": "natural_ru",
                "warnings": []
            }
        }


# === Default fallback plan ===

def make_default_fallback_plan(question: str) -> QueryPlanV2:
    """
    Create a default fallback plan for when Planner LLM fails.

    Uses GENERAL_UNSTRUCTURED intent with portfolio_search_tool.
    This is NOT legacy planning - it's an emergency minimal plan.
    """
    return QueryPlanV2(
        intents=[IntentV2.GENERAL_UNSTRUCTURED],
        entities=[],
        tool_calls=[
            ToolCall(
                tool="portfolio_search_tool",
                args={"query": question, "k": 8}
            )
        ],
        fallback=FallbackConfig(enabled=False),
        limits=LimitsConfig(max_items=8),
        render_style=RenderStyle.BULLETS,
        answer_style=AnswerStyle.NATURAL_RU,
        confidence=0.3,
    )
