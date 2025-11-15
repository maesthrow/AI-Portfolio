from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .api_projects import router as projects_router
from .api_technologies import router as technologies_router
from .api_export import router as export_router

app = FastAPI(title="Content API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    return {"ok": True, "env": "content-api", "log_level": settings.log_level}


app.include_router(projects_router)
app.include_router(technologies_router)
app.include_router(export_router)
