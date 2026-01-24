import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.deps import settings
from app.llm import validate_llm_config
from app.routers import admin, chat, ingest, ingest_batch

logging.basicConfig(
    level=getattr(logging, settings().log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Валидация LLM конфигурации при старте
validate_llm_config()

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
        "planner_llm": s.planner_llm,
        "answer_llm": s.answer_llm,
        "agent_llm": s.agent_llm,
        "embedding_model": s.embedding_model,
    }


@app.get("/meta")
def meta():
    s = settings()
    return {
        "identity_llm": s.identity_llm,
        "planner_llm": s.planner_llm,
        "answer_llm": s.answer_llm,
        "critic_llm": s.critic_llm,
        "agent_llm": s.agent_llm,
        "embedding_model": s.embedding_model,
    }


app.include_router(admin.router)
app.include_router(ingest.router)
app.include_router(ingest_batch.router)
app.include_router(chat.router)
