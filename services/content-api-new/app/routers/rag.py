from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.contact import Contact
from app.models.experience import CompanyExperience
from app.models.focus_area import FocusArea
from app.models.profile import Profile
from app.models.project import Project
from app.models.publication import Publication
from app.models.stats import Stat
from app.models.tech_focus import TechFocus
from app.models.technology import Technology
from app.models.work_approach import WorkApproach
from app.schemas.rag import RagDocumentOut
from app.schemas.rag_export import ExportPayload

router = APIRouter()


@router.get("/documents", response_model=list[RagDocumentOut])
def list_rag_documents(db: Session = Depends(get_db)):
    docs: list[RagDocumentOut] = []

    profile_stmt = select(Profile).order_by(Profile.id.asc()).limit(1)
    profile = db.execute(profile_stmt).scalars().first()
    if profile:
        body_parts = [
            profile.summary_md or "",
            profile.title or "",
            profile.subtitle or "",
            profile.location or "",
            profile.status or "",
        ]
        docs.append(
            RagDocumentOut(
                id=f"profile:{profile.id}",
                type="profile",
                title=profile.full_name,
                body="\n\n".join([p for p in body_parts if p]),
                url=None,
                tags=[],
                metadata={"full_name": profile.full_name},
            )
        )

    exp_stmt = select(CompanyExperience).order_by(
        CompanyExperience.order_index.asc(), CompanyExperience.start_date.desc()
    )
    for exp in db.execute(exp_stmt).scalars().all():
        docs.append(
            RagDocumentOut(
                id=f"experience:{exp.id}",
                type="experience",
                title=f"{exp.role} @ {exp.company_name}",
                body=exp.description_md or "",
                tags=[exp.kind] + ([exp.company_name] if exp.company_name else []),
                metadata={
                    "company": exp.company_name,
                    "kind": exp.kind,
                    "period_start": exp.start_date.isoformat(),
                    "period_end": exp.end_date.isoformat() if exp.end_date else None,
                },
            )
        )

    project_stmt = select(Project).options(joinedload(Project.technologies))
    for proj in db.execute(project_stmt).scalars().unique().all():
        tags = [t.name for t in proj.technologies]
        if proj.domain:
            tags.append(proj.domain)
        docs.append(
            RagDocumentOut(
                id=f"project:{proj.id}",
                type="project",
                title=proj.name,
                body=(proj.long_description_md or proj.description_md or ""),
                url=proj.repo_url or proj.demo_url,
                tags=tags,
                metadata={
                    "domain": proj.domain,
                    "period": proj.period,
                    "company": proj.company_name,
                    "featured": proj.featured,
                },
            )
        )

    pub_stmt = select(Publication).order_by(Publication.order_index.asc(), Publication.id.asc())
    for pub in db.execute(pub_stmt).scalars().all():
        tags = [str(pub.year), pub.source]
        docs.append(
            RagDocumentOut(
                id=f"publication:{pub.id}",
                type="publication",
                title=pub.title,
                body=pub.description_md or pub.title,
                url=pub.url,
                tags=tags,
                metadata={"badge": pub.badge},
            )
        )

    return docs


@router.get("/export", response_model=ExportPayload)
def export_for_rag(db: Session = Depends(get_db)):
    profile_stmt = select(Profile).order_by(Profile.id.asc()).limit(1)
    profile = db.execute(profile_stmt).scalars().first()

    exp_stmt = (
        select(CompanyExperience)
        .options(joinedload(CompanyExperience.projects))
        .order_by(CompanyExperience.order_index.asc(), CompanyExperience.start_date.desc())
    )
    experiences = db.execute(exp_stmt).scalars().unique().all()
    for exp in experiences:
        exp.projects = sorted(exp.projects, key=lambda p: (p.order_index, p.id))

    project_stmt = (
        select(Project)
        .options(joinedload(Project.technologies))
        .order_by(Project.order_index.asc(), Project.id.asc())
    )
    projects = db.execute(project_stmt).scalars().unique().all()

    technologies = (
        db.execute(select(Technology).order_by(Technology.order_index.asc(), Technology.id.asc()))
        .scalars()
        .all()
    )
    publications = (
        db.execute(select(Publication).order_by(Publication.order_index.asc(), Publication.id.asc()))
        .scalars()
        .all()
    )

    focus_areas = (
        db.execute(select(FocusArea).options(joinedload(FocusArea.bullets)).order_by(FocusArea.order_index.asc()))
        .scalars()
        .unique()
        .all()
    )
    for fa in focus_areas:
        fa.bullets = sorted(fa.bullets, key=lambda b: (b.order_index, b.id))
    work_approaches = (
        db.execute(
            select(WorkApproach).options(joinedload(WorkApproach.bullets)).order_by(WorkApproach.order_index.asc())
        )
        .scalars()
        .unique()
        .all()
    )
    for wa in work_approaches:
        wa.bullets = sorted(wa.bullets, key=lambda b: (b.order_index, b.id))
    tech_focus = (
        db.execute(select(TechFocus).options(joinedload(TechFocus.tags)).order_by(TechFocus.order_index.asc()))
        .scalars()
        .unique()
        .all()
    )
    for tf in tech_focus:
        tf.tags = sorted(tf.tags, key=lambda t: (t.order_index, t.id))
    stats = db.execute(select(Stat).order_by(Stat.order_index.asc(), Stat.id.asc())).scalars().all()
    contacts = db.execute(select(Contact).order_by(Contact.order_index.asc(), Contact.id.asc())).scalars().all()

    return ExportPayload(
        profile=profile,
        experiences=experiences,
        projects=projects,
        technologies=technologies,
        publications=publications,
        focus_areas=focus_areas,
        work_approaches=work_approaches,
        tech_focus=tech_focus,
        stats=stats,
        contacts=contacts,
    )
