from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.project import Project
from app.schemas.project import ProjectOut

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
