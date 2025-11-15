from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from .deps import get_db
from .database.models import (
    Project, Technology, Company, Achievement, Document, ProjectKind
)
from .schemas.export_schema import (
    ExportPayload, ProjectExport, TechnologyExport,
    CompanyExport, AchievementExport, DocumentExport
)

router = APIRouter(tags=["export"])


def _period_str(p) -> str:
    if not p.period_start:
        return ""
    start = p.period_start.year
    end = "наст." if not p.period_end else p.period_end.year
    return f"{start}–{end}"


@router.get("/export", response_model=ExportPayload)
def export_all(db: Session = Depends(get_db)):
    # Projects (с технологиями и компанией)
    proj_stmt = (
        select(Project)
        .options(
            selectinload(Project.technologies),
            selectinload(Project.company),
        )
        .order_by(
            (Project.kind == ProjectKind.COMMERCIAL).desc(),
            Project.period_start.desc().nulls_last(),
            Project.weight.desc(),
            Project.id.desc(),
        )
    )
    projects = db.execute(proj_stmt).scalars().all()

    projects_out: list[ProjectExport] = []
    for p in projects:
        projects_out.append(ProjectExport(
            id=p.id,
            name=p.name,
            description=p.description,
            period_start=p.period_start.isoformat() if p.period_start else None,
            period_end=p.period_end.isoformat() if p.period_end else None,
            period=_period_str(p),
            company_id=p.company.id if p.company else None,
            company_name=p.company.name if p.company else None,
            technologies=[t.name for t in (p.technologies or [])],
            kind=p.kind.name if isinstance(p.kind, ProjectKind) else str(p.kind),
            weight=p.weight,
            repo_url=getattr(p, "repo_url", None),
            demo_url=getattr(p, "demo_url", None),
            url=f"/projects/{p.id}",
        ))

    # Технологии (aliases — пока пусто, добавим таблицу позже)
    technologies = db.execute(select(Technology).order_by(Technology.name.asc())).scalars().all()
    technologies_out: list[TechnologyExport] = [
        TechnologyExport(id=t.id, name=t.name, aliases=[], url=f"/tech/{t.id}")
        for t in technologies
    ]

    # Компании
    companies = db.execute(select(Company).order_by(Company.id.asc())).scalars().all()
    companies_out: list[CompanyExport] = [
        CompanyExport(id=c.id, name=c.name, description=c.description, website=c.website)
        for c in companies
    ]

    # Достижения
    achievements = db.execute(select(Achievement).order_by(Achievement.id.asc())).scalars().all()
    achievements_out: list[AchievementExport] = [
        AchievementExport(
            id=a.id,
            project_id=a.project_id,
            title=a.title,
            description=a.description,
            links=a.links or [],
        )
        for a in achievements
    ]

    # Документы
    documents = db.execute(select(Document).order_by(Document.id.asc())).scalars().all()
    documents_out: list[DocumentExport] = [
        DocumentExport(
            id=d.id,
            project_id=d.project_id,
            company_id=d.company_id,
            title=d.title,
            url=d.url,
            doc_type=d.doc_type,
            summary=None,             # при необходимости добавим в модель
            meta=d.meta,
        )
        for d in documents
    ]

    return ExportPayload(
        projects=projects_out,
        technologies=technologies_out,
        companies=companies_out,
        achievements=achievements_out,
        documents=documents_out,
    )
