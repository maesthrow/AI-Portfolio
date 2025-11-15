from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from app.database.models import (
    Company, Project, Document, Achievement,
    Technology, ProjectTechnology, ProjectKind
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
    comp = get_one(session, Company, name="АО «Спарго Технологии»")
    if comp:
        return comp
    comp = Company(
        name="АО «Спарго Технологии»",
        website="https://www.spargo.ru",
        description="ИТ-решения для автоматизации аптек и розничной торговли.",
    )
    session.add(comp)
    session.flush()
    return comp


def ensure_project(session, company: Company) -> Project:
    """
    Поля проекта:
      - name, description
      - period_start / period_end
      - tags: list[str] (JSONB)
      - kind: ProjectKind (COMMERCIAL|PERSONAL)
      - weight: int (сортировка внутри группы)
      - repo_url/demo_url: опционально
    """
    proj = get_one(session, Project, name="F3 TAIL", company_id=company.id)
    if proj:
        # Мягкое «синхро-обновление» ключевых полей (если менялись)
        changed = False
        target = {
            "description": "Сервисы для автоматизации аптек и розничной торговли",
            "period_start": date(2023, 9, 4),
            "period_end": date(2024, 5, 10),
            "tags": ["retail", "pharmacy", "automation"],
            "kind": ProjectKind.COMMERCIAL,
            "weight": 50,
            "repo_url": None,              # "https://github.com/..."
            "demo_url": None,              # "https://demo.example.org/..."
        }
        for field, val in target.items():
            if getattr(proj, field) != val:
                setattr(proj, field, val)
                changed = True
        if changed:
            session.flush()
        return proj

    proj = Project(
        company_id=company.id,
        name="F3 TAIL",
        description="Сервисы для автоматизации аптек и розничной торговли",
        period_start=date(2023, 9, 4),
        period_end=date(2024, 5, 10),
        tags=["retail", "pharmacy", "automation"],
        kind=ProjectKind.COMMERCIAL,
        weight=50,
        repo_url=None,
        demo_url=None,
    )
    session.add(proj)
    session.flush()
    return proj


def ensure_project_techs(session, project: Project, tech_names: Iterable[str]) -> None:
    for name in tech_names:
        tech = get_or_create_tech(session, name=name)
        exists = session.execute(
            select(ProjectTechnology).filter_by(project_id=project.id, technology_id=tech.id)
        ).scalar_one_or_none()
        if not exists:
            session.add(ProjectTechnology(project_id=project.id, technology_id=tech.id))


def ensure_achievements(session, project: Project) -> None:
    items: Iterable[tuple[str, str, list[str]]] = [
        (
            "Ускорение обмена данными с Единым Справочником",
            "Оптимизировал код сервиса, выполняющего обмен на стороне аптек между БД и "
            "сервисом Единого Справочника; скорость обмена выросла более чем в 3 раза.",
            [],
        ),
        (
            "Сервис мониторинга и логирования сбоев",
            "Разработал сервис мониторинга и логирования сбоев работы служб на сервере.",
            [],
        ),
        (
            "Telegram-бот службы поддержки",
            "Разработал бота поддержки; предложил и реализовал фичи: удобное кнопочное меню "
            "и сценарии на aiogram-dialog, подтверждение регистрации заявки.",
            [],
        ),
    ]
    for title, descr, links in items:
        ach = get_one(session, Achievement, project_id=project.id, title=title)
        if ach:
            # опционально — мягко синхронизировать описание/ссылки, если хочешь
            continue
        session.add(Achievement(
            project_id=project.id,
            title=title,
            description=descr,
            links=links or [],
        ))


def ensure_documents(session, project: Project, company: Company) -> None:
    docs = [
        ("Архитектура F3 TAIL", "https://example.org/f3-tail-arch.pdf", "diagram"),
        ("Мониторинг и алерты — спецификация", "https://example.org/f3-tail-monitoring.html", "spec"),
        ("Сценарии бота поддержки (aiogram-dialog)", "https://example.org/f3-tail-bot-flows.pdf", "diagram"),
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
            # Язык/фреймворки
            "Python 3.9", "FastAPI", "Pydantic", "APScheduler", "asyncio",
            "SQLAlchemy", "PostgreSQL",
            # Боты
            "aiogram", "aiogram-dialog",
            # Инфраструктура
            "Docker",
        ])

        ensure_achievements(db, project)
        ensure_documents(db, project, company)

        db.commit()
        print("✅ Seed completed: АО «Спарго Технологии» / F3 TAIL")


if __name__ == "__main__":
    run()
