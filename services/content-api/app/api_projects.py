from typing import List, Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import Session, selectinload

from .database.models import Project, ProjectTechnology, ProjectKind
from .schemas.project_schema import ProjectOut, ProjectDetailOut
from .deps import get_db

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    technology_id: Optional[List[int]] = Query(
        None,
        description="Фильтр по технологиям (?technology_id=1&technology_id=2)",
    ),
):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.company),
            selectinload(Project.technologies),
        )
    )

    # --- фильтр: проект должен содержать ВСЕ выбранные технологии (AND) ---
    if technology_id:
        tech_ids = [int(t) for t in technology_id if t is not None]
        if tech_ids:
            subq = (
                select(ProjectTechnology.project_id)
                .where(ProjectTechnology.technology_id.in_(tech_ids))
                .group_by(ProjectTechnology.project_id)
                .having(func.count(distinct(ProjectTechnology.technology_id)) == len(tech_ids))
            )
            stmt = stmt.where(Project.id.in_(subq))

    # --- сортировка ---
    stmt = stmt.order_by(
        (Project.kind == ProjectKind.COMMERCIAL).desc(),   # коммерческие раньше
        Project.period_start.desc().nulls_last(),          # свежие раньше
        Project.weight.desc().nulls_last(),                # вес по убыванию
        Project.id.desc(),                                 # fallback
    )

    items = db.execute(stmt).scalars().all()
    return [ProjectOut.from_orm_and_format(p) for p in items]


@router.get("/projects/{pid}", response_model=ProjectDetailOut)
def get_project(pid: int, db: Session = Depends(get_db)):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.company),
            selectinload(Project.technologies),
            selectinload(Project.achievements),
            selectinload(Project.documents),
        )
        .where(Project.id == pid)
        .limit(1)
    )
    p = db.execute(stmt).scalars().first()
    if not p:
        raise HTTPException(404, "Project not found")
    return ProjectDetailOut.from_orm_and_format(p)
