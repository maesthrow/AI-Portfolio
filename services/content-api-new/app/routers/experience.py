from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.experience import CompanyExperience
from app.models.experience_project import ExperienceProject
from app.schemas.experience import CompanyExperienceDetail, CompanyExperienceOut, ExperienceProjectOut

router = APIRouter()


@router.get("/", response_model=list[CompanyExperienceOut])
def list_companies(kind: str | None = None, db: Session = Depends(get_db)):
    effective_kind = kind or "commercial"
    stmt = (
        select(CompanyExperience)
        .where(CompanyExperience.kind == effective_kind)
        .order_by(CompanyExperience.order_index.asc(), CompanyExperience.start_date.desc())
    )
    results = db.execute(stmt).scalars().all()
    return results


@router.get("/{company_slug}", response_model=CompanyExperienceDetail)
def get_company_detail(company_slug: str, db: Session = Depends(get_db)):
    company = (
        db.execute(
            select(CompanyExperience)
            .options(joinedload(CompanyExperience.projects))
            .where(CompanyExperience.company_slug == company_slug)
            .where(CompanyExperience.kind != "personal")
        )
        .scalars()
        .first()
    )

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    projects_stmt = (
        select(ExperienceProject)
        .where(ExperienceProject.experience_id == company.id)
        .order_by(ExperienceProject.order_index.asc())
    )
    projects = db.execute(projects_stmt).scalars().all()

    return CompanyExperienceDetail(company=company, projects=projects)
