"""
QueryPlanV3 schemas with parameterized intents and filters.

Based on TZ v3: Universal intents + technology taxonomy + strict role control.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TechCategory(str, Enum):
    """Technology category taxonomy (P0)."""
    LANGUAGE = "language"
    DATABASE = "database"
    FRAMEWORK = "framework"
    ML_FRAMEWORK = "ml_framework"
    TOOL = "tool"
    CLOUD = "cloud"
    LIBRARY = "library"
    CONCEPT = "concept"  # For RAG/ReAct/LLM as concepts
    OTHER = "other"


class InfoNeed(str, Enum):
    """Type of information needed from the query."""
    SUMMARY = "summary"
    DETAILS = "details"
    ACHIEVEMENTS = "achievements"
    TECH_STACK = "tech_stack"
    USAGE = "usage"
    RESPONSIBILITIES = "responsibilities"
    DATES = "dates"
    ROLE = "role"


class ScopeLevel(str, Enum):
    """Scope level for queries."""
    GLOBAL = "global"
    COMPANY = "company"
    PROJECT = "project"


class IntentV3(str, Enum):
    """
    Universal intents for QueryPlanV3.

    Same as V2 but used with parameters (slots/filters).
    """
    CURRENT_JOB = "current_job"
    PROJECT_DETAILS = "project_details"
    PROJECT_ACHIEVEMENTS = "project_achievements"
    PROJECT_TECH_STACK = "project_tech_stack"
    TECHNOLOGY_OVERVIEW = "technology_overview"
    TECHNOLOGY_USAGE = "technology_usage"
    EXPERIENCE_SUMMARY = "experience_summary"
    CONTACTS = "contacts"
    GENERAL_UNSTRUCTURED = "general_unstructured"


class RenderStyleV3(str, Enum):
    """Deterministic rendering styles."""
    BULLETS = "bullets"
    GROUPED_BULLETS = "grouped_bullets"
    SHORT = "short"
    TABLE = "table"
    PARAGRAPH = "paragraph"


class AnswerStyleV3(str, Enum):
    """Answer generation styles."""
    NATURAL_RU = "natural_ru"
    CONCISE = "concise"
    DETAILED = "detailed"
    ENUMERATION = "enumeration"


# ========== ScopeGuard Schemas ==========

class ScopeDecision(BaseModel):
    """
    Result of ScopeGuard evaluation.

    Determines if question is within portfolio scope.
    """
    in_scope: bool = Field(
        description="Whether question is about the portfolio"
    )
    reason: str = Field(
        default="",
        description="Reason for decision (for debugging)"
    )
    suggested_prompts: list[str] = Field(
        default_factory=list,
        description="Suggested portfolio questions if out of scope"
    )
    category: Literal["portfolio", "small_talk", "off_topic", "harmful"] = Field(
        default="portfolio",
        description="Question category"
    )


# ========== TechFilter Schemas ==========

class TechFilter(BaseModel):
    """
    Technology filtering parameters.

    Used for technology_overview and technology_usage intents.
    """
    category: TechCategory | None = Field(
        default=None,
        description="Filter by technology category (language/database/etc.)"
    )
    tags_any: list[str] = Field(
        default_factory=list,
        description="Match any of these tags (ml, rag, llm, etc.)"
    )
    strict: bool = Field(
        default=True,
        description="If true, only return exact category matches"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "category": "database",
                "tags_any": [],
                "strict": True
            }
        }


class Scope(BaseModel):
    """
    Query scope parameters.

    Defines the context level for queries.
    """
    level: ScopeLevel = Field(
        default=ScopeLevel.GLOBAL,
        description="Scope level: global/company/project"
    )
    company_id: str | None = Field(
        default=None,
        description="Company ID for company-level queries (e.g., 'company:alor')"
    )
    project_id: str | None = Field(
        default=None,
        description="Project ID for project-level queries (e.g., 'project:ai-portfolio')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "level": "company",
                "company_id": "company:alor",
                "project_id": None
            }
        }


class EntitiesV3(BaseModel):
    """
    Extracted entities from user question.

    Simplified structure with canonical IDs.
    """
    company_id: str | None = Field(
        default=None,
        description="Company ID (e.g., 'company:alor')"
    )
    project_id: str | None = Field(
        default=None,
        description="Project ID (e.g., 'project:ai-portfolio')"
    )
    technology_key: str | None = Field(
        default=None,
        description="Technology key/slug (e.g., 'rag', 'python', 'postgresql')"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "company_id": None,
                "project_id": None,
                "technology_key": "rag"
            }
        }


class ToolCallV3(BaseModel):
    """
    Tool invocation with extended arguments.

    Supports filters and scope parameters.
    """
    tool: str = Field(
        description="Tool name: graph_query_tool, portfolio_search_tool"
    )
    args: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool arguments including filters"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "tool": "graph_query_tool",
                "args": {
                    "intent": "technology_overview",
                    "tech_category": "database",
                    "scope": "global"
                }
            }
        }


class AnswerFormatV3(BaseModel):
    """Answer formatting preferences."""
    format: RenderStyleV3 = Field(default=RenderStyleV3.BULLETS)
    lang: Literal["ru", "en"] = Field(default="ru")


class LimitsConfigV3(BaseModel):
    """Search and rendering limits."""
    max_items: int = Field(default=10, ge=1, le=50)
    max_groups: int = Field(default=4, ge=1, le=10)
    max_paragraphs: int = Field(default=4, ge=1, le=10)


class FallbackConfigV3(BaseModel):
    """Fallback behavior configuration."""
    enabled: bool = Field(default=True)
    tool: str = Field(default="portfolio_search_tool")
    when: list[str] = Field(
        default_factory=lambda: ["NO_RESULTS", "LOW_COVERAGE"]
    )


class QueryPlanV3(BaseModel):
    """
    LLM-generated query plan with parameterized intents.

    Main output of Planner LLM v3.
    Uses universal intents with slots/filters for specificity.

    Based on TZ section 4.1.

    NOTE: Maintains backward compatibility with QueryPlanV2 field names
    (intents, tool_calls, render_style, answer_style) while adding new V3 features.
    """
    # Backward compatible fields (same as V2)
    intents: list[IntentV3] = Field(
        default_factory=list,
        description="Detected intents (primary first)"
    )
    entities: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted entities (for compatibility with V2)"
    )
    tool_calls: list[ToolCallV3] = Field(
        default_factory=list,
        description="Planned tool invocations"
    )
    fallback: FallbackConfigV3 = Field(
        default_factory=FallbackConfigV3,
        description="Fallback configuration"
    )
    limits: LimitsConfigV3 = Field(
        default_factory=LimitsConfigV3,
        description="Search and render limits"
    )
    render_style: RenderStyleV3 = Field(
        default=RenderStyleV3.BULLETS,
        description="Rendering style for facts"
    )
    answer_style: AnswerStyleV3 = Field(
        default=AnswerStyleV3.NATURAL_RU,
        description="Answer generation style"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Planner's confidence in the plan"
    )

    # New V3 fields
    tech_filter: TechFilter | None = Field(
        default=None,
        description="Technology filtering parameters (V3 feature)"
    )
    scope: Scope | None = Field(
        default=None,
        description="Query scope parameters (V3 feature)"
    )
    info_need: InfoNeed = Field(
        default=InfoNeed.SUMMARY,
        description="Type of information needed (V3 feature)"
    )

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "intent": "technology_overview",
                    "entities": {"technology_key": None},
                    "tech_filter": {"category": "language", "strict": True},
                    "scope": {"level": "global"},
                    "info_need": "summary",
                    "tool_plan": [
                        {"tool": "graph_query_tool", "args": {"intent": "technology_overview", "tech_category": "language"}}
                    ],
                    "answer_style": {"format": "bullets", "lang": "ru"},
                    "confidence": 0.9
                },
                {
                    "intent": "experience_summary",
                    "entities": {"company_id": "company:alor"},
                    "tech_filter": {},
                    "scope": {"level": "company", "company_id": "company:alor"},
                    "info_need": "responsibilities",
                    "tool_plan": [
                        {"tool": "graph_query_tool", "args": {"intent": "experience_summary", "entity_id": "company:alor", "scope": "company"}}
                    ],
                    "answer_style": {"format": "bullets", "lang": "ru"},
                    "confidence": 0.85
                }
            ]
        }


# ========== FactBundle Schemas ==========

class FactBundleItem(BaseModel):
    """
    Single fact with source traceability.

    Part of FactBundle - used for grounding verification.
    """
    type: str = Field(description="Fact type: achievement, technology, experience, etc.")
    text: str = Field(description="Fact content")
    entity_id: str | None = Field(default=None, description="Source entity ID")
    category: TechCategory | None = Field(default=None, description="Technology category if applicable")
    metadata: dict[str, Any] = Field(default_factory=dict)


class FactBundle(BaseModel):
    """
    Collection of verified facts for Answer LLM.

    Used for grounding verification - all named entities
    in the answer must be present in this bundle.
    """
    facts: list[FactBundleItem] = Field(default_factory=list)
    technologies: list[str] = Field(
        default_factory=list,
        description="List of technology names mentioned in facts"
    )
    companies: list[str] = Field(
        default_factory=list,
        description="List of company names mentioned in facts"
    )
    projects: list[str] = Field(
        default_factory=list,
        description="List of project names mentioned in facts"
    )
    roles: list[str] = Field(
        default_factory=list,
        description="List of roles mentioned in facts"
    )
    dates: list[str] = Field(
        default_factory=list,
        description="List of dates/periods mentioned in facts"
    )

    def get_all_entities(self) -> set[str]:
        """Get all named entities for grounding check."""
        entities = set()
        entities.update(t.lower() for t in self.technologies)
        entities.update(c.lower() for c in self.companies)
        entities.update(p.lower() for p in self.projects)
        entities.update(r.lower() for r in self.roles)
        return entities


# ========== NormalizerOutput Schemas ==========

class NormalizerOutput(BaseModel):
    """
    Output from deterministic fact normalization.

    After Normalizer applies filtering rules based on intent/filters.
    """
    filtered_facts: list[FactBundleItem] = Field(
        default_factory=list,
        description="Facts after filtering"
    )
    removed_count: int = Field(
        default=0,
        description="Number of facts removed by filtering"
    )
    rules_applied: list[str] = Field(
        default_factory=list,
        description="List of normalization rules applied"
    )
    rendered_text: str = Field(
        default="",
        description="Rendered facts as text for Answer LLM"
    )


# ========== GroundingVerifier Schemas ==========

class GroundingResult(BaseModel):
    """
    Result of grounding verification.

    Checks that answer only mentions entities from FactBundle.
    """
    grounded: bool = Field(
        default=True,
        description="Whether answer is fully grounded in facts"
    )
    ungrounded_entities: list[str] = Field(
        default_factory=list,
        description="Entities mentioned in answer but not in facts"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Grounding confidence score"
    )
    suggested_rewrite: str | None = Field(
        default=None,
        description="Rewritten answer if grounding failed"
    )
    action: Literal["accept", "rewrite", "refuse"] = Field(
        default="accept",
        description="Action to take based on grounding result"
    )


# ========== Helper Functions ==========

def normalize_plan_values(plan: QueryPlanV3) -> QueryPlanV3:
    """
    Canonicalize plan values (synonym mapping).

    Maps common variations to standard values:
    - bulleted_list -> bullets
    - grouped_list -> grouped_bullets
    - etc.
    """
    data = plan.model_dump()

    # Render style normalization
    style_map = {
        "bulleted_list": "bullets",
        "bullet_list": "bullets",
        "list": "bullets",
        "grouped_list": "grouped_bullets",
        "grouped": "grouped_bullets",
        "brief": "short",
        "compact": "short",
    }

    if "answer_style" in data and "format" in data["answer_style"]:
        fmt = data["answer_style"]["format"]
        if isinstance(fmt, str) and fmt.lower() in style_map:
            data["answer_style"]["format"] = style_map[fmt.lower()]

    # Tech category normalization
    category_map = {
        "lang": "language",
        "programming_language": "language",
        "db": "database",
        "datastore": "database",
        "lib": "library",
        "ml": "ml_framework",
        "ai": "concept",
    }

    if "tech_filter" in data and "category" in data["tech_filter"]:
        cat = data["tech_filter"]["category"]
        if isinstance(cat, str) and cat.lower() in category_map:
            data["tech_filter"]["category"] = category_map[cat.lower()]

    return QueryPlanV3.model_validate(data)


def make_default_plan_v3(question: str) -> QueryPlanV3:
    """
    Create default fallback plan for when planning fails.
    """
    return QueryPlanV3(
        intent=IntentV3.GENERAL_UNSTRUCTURED,
        entities=EntitiesV3(),
        tech_filter=TechFilter(),
        scope=Scope(level=ScopeLevel.GLOBAL),
        info_need=InfoNeed.SUMMARY,
        tool_plan=[
            ToolCallV3(
                tool="portfolio_search_tool",
                args={"query": question, "k": 8}
            )
        ],
        answer_style=AnswerFormatV3(format=RenderStyleV3.BULLETS, lang="ru"),
        fallback=FallbackConfigV3(enabled=False),
        limits=LimitsConfigV3(max_items=8),
        confidence=0.3,
    )
