from typing import List, Optional
from pydantic import BaseModel, Field


class ProjectExport(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    period_start: Optional[str] = None   # ISO YYYY-MM-DD
    period_end: Optional[str] = None     # ISO YYYY-MM-DD | None
    period: Optional[str] = None         # "YYYY–YYYY|наст."
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    kind: str  # "COMMERCIAL" | "PERSONAL"
    weight: int
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    url: Optional[str] = None


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
