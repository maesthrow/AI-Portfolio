from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import (
    contacts,
    experience,
    focus_areas,
    hero_tags,
    profile,
    projects,
    publications,
    rag,
    section_meta,
    stats,
    tech_focus,
    work_approaches,
)

app = FastAPI(title="AI Portfolio Content API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(experience.router, prefix="/api/v1/experience", tags=["experience"])
app.include_router(stats.router, prefix="/api/v1/stats", tags=["stats"])
app.include_router(tech_focus.router, prefix="/api/v1/tech-focus", tags=["tech-focus"])
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(publications.router, prefix="/api/v1/publications", tags=["publications"])
app.include_router(contacts.router, prefix="/api/v1/contacts", tags=["contacts"])
app.include_router(rag.router, prefix="/api/v1/rag", tags=["rag"])
app.include_router(hero_tags.router, prefix="/api/v1/hero-tags", tags=["hero-tags"])
app.include_router(focus_areas.router, prefix="/api/v1/focus-areas", tags=["focus-areas"])
app.include_router(work_approaches.router, prefix="/api/v1/work-approaches", tags=["work-approaches"])
app.include_router(section_meta.router, prefix="/api/v1/section-meta", tags=["section-meta"])


@app.get("/healthz")
def healthz():
    return {"ok": True, "env": settings.app_env, "log_level": settings.log_level}
