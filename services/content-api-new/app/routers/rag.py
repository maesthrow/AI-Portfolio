from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.experience import Experience
from app.models.profile import Profile
from app.models.project import Project
from app.models.publication import Publication
from app.schemas.rag import RagDocumentOut

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

    exp_stmt = select(Experience).order_by(Experience.order_index.asc(), Experience.start_date.desc())
    for exp in db.execute(exp_stmt).scalars().all():
        docs.append(
            RagDocumentOut(
                id=f"experience:{exp.id}",
                type="experience",
                title=f"{exp.role} — {exp.company_name}",
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
