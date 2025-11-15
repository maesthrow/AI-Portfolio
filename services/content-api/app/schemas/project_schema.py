from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from .achievement_schema import AchievementOut
from .document_schema import DocumentOut
from ..database.models import ProjectKind


def _fmt_month(d: Optional[date]) -> Optional[str]:
    """MM.YYYY для даты или None."""
    return d.strftime("%m.%Y") if d else None


def _fmt_period(start: Optional[date], end: Optional[date]) -> Optional[str]:
    """
    Формат периода:
      - MM.YYYY–MM.YYYY
      - MM.YYYY–наст. (если конец отсутствует)
      - None (если обе даты отсутствуют)
    """
    s = _fmt_month(start)
    e = _fmt_month(end)
    if s and e:
        return f"{s}–{e}"
    if s and not e:
        return f"{s}–наст."
    return None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    period: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    company_name: str | None = None
    company_website: str | None = None
    kind: str  # "COMMERCIAL" | "PERSONAL"
    weight: int
    repo_url: str | None = None
    demo_url: str | None = None

    @classmethod
    def from_orm_and_format(cls, p) -> "ProjectOut":
        """
        Собираем DTO из ORM-модели Project:
        - summary берём из p.description (fallback на p.summary, если вдруг есть)
        - period форматируем через _fmt_period(...)
        - technologies — список имён технологий
        """
        period = _fmt_period(getattr(p, "period_start", None), getattr(p, "period_end", None))
        techs = [t.name for t in (getattr(p, "technologies", []) or [])]
        company = getattr(p, "company", None)

        return cls(
            id=p.id,
            name=p.name,
            description=p.description,
            period=period,
            technologies=techs,
            company_name=getattr(company, "name", None),
            company_website=getattr(company, "website", None),
            kind=p.kind.name if isinstance(p.kind, ProjectKind) else str(p.kind),
            weight=p.weight,
            repo_url=getattr(p, "repo_url", None),
            demo_url=getattr(p, "demo_url", None),
        )

    model_config = {"from_attributes": True}


class ProjectDetailOut(ProjectOut):
    achievements: List[AchievementOut] = Field(default_factory=list)
    documents: List[DocumentOut] = Field(default_factory=list)

    @classmethod
    def from_orm_and_format(cls, p) -> "ProjectDetailOut":
        base = ProjectOut.from_orm_and_format(p)
        achievements = [
            AchievementOut(
                title=a.title,
                description=a.description,
                links=list(a.links or []),
            )
            for a in (getattr(p, "achievements", []) or [])
        ]
        documents = [
            DocumentOut(
                title=d.title,
                url=d.url,
                doc_type=d.doc_type,
            )
            for d in (getattr(p, "documents", []) or [])
        ]
        return cls(**base.model_dump(), achievements=achievements, documents=documents)
