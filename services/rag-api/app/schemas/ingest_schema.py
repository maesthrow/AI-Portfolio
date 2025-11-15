from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


class IngestItem(BaseModel):
    id: str = Field(..., description="doc id, например 'project:1'")
    text: str
    metadata: Dict[str, Any] | None = None


class IngestRequest(BaseModel):
    collection: Optional[str] = None
    items: List[IngestItem]


# --- структуры из /export (Content API) ---
class ProjectExport(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    period: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    kind: Optional[Literal["commercial", "personal"]] = None
    weight: Optional[int] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None

    @field_validator("kind", mode="before")
    @classmethod
    def _normalize_kind(cls, v):
        # принимаем Enum/строку/любой регистр
        if v is None:
            return None
        if hasattr(v, "value"):
            v = v.value  # Enum -> str
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("commercial", "personal"):
                return s
        # мягко упасть с понятной ошибкой
        raise ValueError("Input should be 'commercial' or 'personal'")


class TechnologyExport(BaseModel):
    id: int
    name: str
    aliases: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class CompanyExport(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    website: Optional[str] = None


class AchievementExport(BaseModel):
    id: int
    project_id: int
    title: str
    description: Optional[str] = None
    links: List[str] = Field(default_factory=list)


class DocumentExport(BaseModel):
    id: int
    project_id: Optional[int] = None
    company_id: Optional[int] = None
    title: str
    url: str
    doc_type: Optional[str] = None
    summary: Optional[str] = None
    meta: Optional[dict] = None


class ExportPayload(BaseModel):
    projects: List[ProjectExport]
    technologies: List[TechnologyExport]
    companies: List[CompanyExport] = Field(default_factory=list)
    achievements: List[AchievementExport] = Field(default_factory=list)
    documents: List[DocumentExport] = Field(default_factory=list)
