from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from app.database.models import (
    Company, Project, Document, Achievement,
    Technology, ProjectTechnology, ProjectKind,   # ← добавили ProjectKind
)

# автономная сессия, чтобы сидер можно было гонять отдельно
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_one(session, model, **filters):
    return session.execute(select(model).filter_by(**filters)).scalar_one_or_none()


def get_or_create_tech(session, name: str, description: str | None = None) -> Technology:
    t = get_one(session, Technology, name=name)
    if t:
        return t
    t = Technology(name=name, description=description)
    session.add(t)
    session.flush()
    return t


def ensure_company(session) -> Company:
    comp = get_one(session, Company, name="Aston")
    if comp:
        return comp
    comp = Company(
        name="Aston",
        website="https://astondevs.ru",
        description="Aston — разработка корпоративных решений и платформ.",
    )
    session.add(comp)
    session.flush()
    return comp


def ensure_project(session, company: Company) -> Project:
    """
    Поля проекта соответствуют новой модели:
      - name, description
      - period_start/period_end
      - tags: list[str] (JSONB)
      - kind: ProjectKind
      - weight: int
      - repo_url/demo_url: Optional[str]
    """
    proj = get_one(session, Project, company_id=company.id, name="t2 - Нейросети")

    target_defaults = {
        "description": (
            "Проект компании t2 по разработке сервисов на базе ML-решений (LLM и CV): "
            "от подготовки данных и обучения до развертывания инференса, интеграции "
            "с внутренними API/документооборотом и генерации отчетов."
        ),
        "period_start": date(2024, 10, 28),   # 2024/25
        "period_end": None,
        "tags": ["ml", "llm", "cv"],
        "kind": ProjectKind.COMMERCIAL,
        "weight": 50,
        "repo_url": None,
        "demo_url": None,
    }

    if proj:
        # мягкая синхронизация: обновляем только если отличается
        changed = False
        for field, val in target_defaults.items():
            if getattr(proj, field) != val:
                setattr(proj, field, val)
                changed = True
        if changed:
            session.flush()
        return proj

    proj = Project(
        company_id=company.id,
        name="t2 - Нейросети",
        **target_defaults,
    )
    session.add(proj)
    session.flush()
    return proj


def ensure_project_techs(session, project: Project, tech_names: Iterable[str]) -> None:
    for name in tech_names:
        tech = get_or_create_tech(session, name=name)
        exists = session.execute(
            select(ProjectTechnology).filter_by(
                project_id=project.id, technology_id=tech.id
            )
        ).scalar_one_or_none()
        if not exists:
            session.add(ProjectTechnology(project_id=project.id, technology_id=tech.id))


def ensure_achievements(session, project: Project) -> None:
    items: Iterable[tuple[str, str, list[str]]] = [
        (
            "Сервис компьютерного зрения для ребрендинга t2/Tele2",
            "Спроектировал и внедрил сервис компьютерного зрения: обучил CV-модель (YOLOv8) "
            "для распознавания бренда на изображениях (старый «Tele2» / новый «t2») и "
            "автоматизировал формирование отчётов по торговым точкам. Решение стало ключевым "
            "элементом процесса ребрендинга в 2024/25.",
            [],
        ),
        (
            "Telegram-бот с LLM + RAG для расчёта штрафов по договорам",
            "Создал Telegram-бота с интеграцией LLM + RAG для расчёта штрафов по договорам. "
            "Бот использует парсинг и анализ текста, семантический + векторный поиск и "
            "цепочки рассуждений для выбора подходящего условия договора и вывода формулы "
            "для расчёта, после чего выполняет вычисления через вызов инструмента для калькуляции.",
            [],
        ),
        (
            "MVP бэкенда авто-обучения и инференса CV-моделей",
            "Разработал до стадии MVP бэкенд веб-сервиса (FastAPI) автоматизированного обучения и "
            "использования CV-моделей: создание отдельных проектов, загрузка датасетов, запуск задач "
            "обучения, регистрация версий в MLflow Model Registry, инференс моделей.",
            [],
        ),
    ]
    for title, descr, links in items:
        ach = get_one(session, Achievement, project_id=project.id, title=title)
        if ach:
            continue
        session.add(Achievement(
            project_id=project.id,
            title=title,
            description=descr,
            links=links or [],
        ))


def ensure_documents(session, project: Project, company: Company) -> None:
    docs = [
        ("Архитектура сервиса LLM + RAG", "https://example.org/aston-llm-rag-arch.pdf", "diagram"),
        ("Схема CV-пайплайна t2", "https://example.org/aston-cv-pipeline-diagram.pdf", "diagram"),
        ("Отчёт по качеству (валидация)", "https://example.org/aston-metrics-report.html", "report"),
    ]
    for title, url, doc_type in docs:
        if not get_one(session, Document, title=title):
            session.add(Document(
                title=title,
                url=url,
                doc_type=doc_type,
                project_id=project.id,
                company_id=company.id,
                meta={"seed": True},
            ))


def run():
    with SessionLocal() as db:
        company = ensure_company(db)
        project = ensure_project(db, company)

        ensure_project_techs(db, project, [
            # Язык/рантайм и фреймворки
            "Python 3.12", "FastAPI", "Pydantic", "SQLAlchemy", "Alembic",
            "asyncio", "aiogram", "Celery",
            # Хранилища и брокеры
            "PostgreSQL", "Redis",
            # Сервинг/инфраструктура
            "Docker", "Azure DevOps", "GitLab",
            # LLM/инференс
            "vLLM", "LiteLLM", "Ollama", "MLflow",
            # CV/ML-фреймворки
            "YOLO (Ultralytics)", "Detectron2",
            # RAG/векторка/агенты
            "RAG", "LangChain", "LangGraph", "ChromaDB", "MCP",
        ])

        ensure_achievements(db, project)
        ensure_documents(db, project, company)

        db.commit()
        print("✅ Seed completed: Aston / t2 - Нейросети")


if __name__ == "__main__":
    run()
