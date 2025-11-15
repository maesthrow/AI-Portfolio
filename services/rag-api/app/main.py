from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .deps import settings
from .api_admin import router as admin_router
from .api_ingest import router as ingest_router
from .api_ingest_batch import router as ingest_batch_router
from .api_ask import router as ask_router

app = FastAPI(title="RAG API", docs_url="/api/swagger")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings().frontend_origin)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    s = settings()
    return {
        "ok": True,
        "env": "rag-api",
        "log_level": s.log_level,
        "collection": s.chroma_collection,
        "chat_model": s.chat_model,
        "embedding_model": s.embedding_model,
    }


app.include_router(admin_router)
app.include_router(ingest_router)
app.include_router(ingest_batch_router)
app.include_router(ask_router)
