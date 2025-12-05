from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.project import Project
from app.schemas.project import ProjectDetailOut, ProjectOut

router = APIRouter()


@router.get("/", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db), featured: Optional[bool] = Query(default=None)
):
    stmt = select(Project).options(joinedload(Project.technologies))
    if featured is True:
        stmt = stmt.where(Project.featured.is_(True))
    stmt = stmt.order_by(Project.order_index.asc(), Project.id.asc())
    projects = db.execute(stmt).scalars().unique().all()
    return [
        ProjectOut(
            id=p.id,
            name=p.name,
            slug=p.slug,
            description_md=p.description_md,
            period=p.period,
            company_name=p.company_name,
            company_website=p.company_website,
            domain=p.domain,
            featured=p.featured,
            repo_url=p.repo_url,
            demo_url=p.demo_url,
            technologies=[t.name for t in p.technologies],
        )
        for p in projects
    ]


@router.get("/{slug}", response_model=ProjectDetailOut)
def get_project_by_slug(slug: str, db: Session = Depends(get_db)):
    stmt = (
        select(Project)
        .options(joinedload(Project.technologies))
        .where(Project.slug == slug)
    )
    project = db.execute(stmt).unique().scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectDetailOut(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description_md=project.description_md,
        long_description_md=project.long_description_md,
        period=project.period,
        company_name=project.company_name,
        company_website=project.company_website,
        domain=project.domain,
        featured=project.featured,
        repo_url=project.repo_url,
        demo_url=project.demo_url,
        technologies=[t.name for t in project.technologies],
    )
