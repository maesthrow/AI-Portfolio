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
    company_name = 'АО «РКЦ «Прогресс»'   # безопасно: внешние одинарные кавычки
    comp = get_one(session, Company, name=company_name)
    if comp:
        return comp
    comp = Company(
        name=company_name,
        website="https://samspace.ru",
        description="Системы и ПО. Проект: СКИО — система контроля испытательного оборудования.",
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
    proj = get_one(session, Project, company_id=company.id, name="СКИО")
    target_defaults = {
        "description": "Система контроля испытательного оборудования.",
        "period_start": date(2022, 8, 1),
        "period_end": date(2023, 9, 1),
        "tags": ["db", "backend", "test-equipment"],
        "kind": ProjectKind.COMMERCIAL,
        "weight": 50,
        "repo_url": None,
        "demo_url": None,
    }

    if proj:
        # мягко синхронизируем при повторных запусках
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
        name="СКИО",
        **target_defaults,
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
            "Серверная часть и БД для СКИО",
            "Спроектировал БД (таблицы, индексы, представления), реализовал серверные скрипты на "
            "Python (SQLAlchemy + psycopg), отчёты (CSV/COPY), тесты (pytest).",
            [],
        ),
    ]
    for title, descr, links in items:
        ach = get_one(session, Achievement, project_id=project.id, title=title)
        if ach:
            # при желании можно синхронизировать описание/ссылки
            continue
        session.add(Achievement(
            project_id=project.id,
            title=title,
            description=descr,
            links=links or [],
        ))


def ensure_documents(session, project: Project, company: Company) -> None:
    docs = [
        ("СКИО — схема БД", "https://example.org/skio-db-schema.pdf", "diagram"),
        ("СКИО — отчёты CSV/COPY", "https://example.org/skio-reports-notes.html", "spec"),
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
            "Python 3.9", "SQLAlchemy", "psycopg", "PostgreSQL", "pytest",
        ])

        ensure_achievements(db, project)
        ensure_documents(db, project, company)

        db.commit()
        print("✅ Seed completed: АО «РКЦ «Прогресс» / СКИО")


if __name__ == "__main__":
    run()
