from typing import List, Optional
from pydantic import BaseModel

# Те же поля, что и в /export (Content API)


class ProjectExport(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    period: Optional[str] = None
    company_id: Optional[int] = None
    company_name: Optional[str] = None
    technologies: List[str] = []
    url: Optional[str] = None


class TechnologyExport(BaseModel):
    id: int
    name: str
    aliases: List[str] = []
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
    links: List[str] = []


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
    companies: List[CompanyExport] = []
    achievements: List[AchievementExport] = []
    documents: List[DocumentExport] = []
