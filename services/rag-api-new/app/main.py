import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import settings
from app.routers import admin, chat, ingest, ingest_batch

logging.basicConfig(
    level=getattr(logging, settings().log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


app = FastAPI(title="RAG API (new)", docs_url="/api/swagger")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings().frontend_origin), str(settings().frontend_local_ip)],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
def healthz():
    s = settings()
    return {
        "ok": True,
        "env": "rag-api-new",
        "log_level": s.log_level,
        "collection": s.chroma_collection,
        "chat_model": s.chat_model,
        "embedding_model": s.embedding_model,
    }


@app.get("/meta")
def meta():
    s = settings()
    return {
        "chat_model": s.chat_model,
        "embedding_model": s.embedding_model,
    }


app.include_router(admin.router)
app.include_router(ingest.router)
app.include_router(ingest_batch.router)
app.include_router(chat.router)
