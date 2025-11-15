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
    comp = get_one(session, Company, name="ООО «АЛОР +»")
    if comp:
        return comp
    comp = Company(
        name="ООО «АЛОР +»",
        website="https://www.alorbroker.ru",
        description="АЛОР БРОКЕР — услуги на рынке ценных бумаг для физ. и юр. лиц.",
    )
    session.add(comp)
    session.flush()
    return comp


def ensure_project(session, company: Company) -> Project:
    """
    Поля проекта под новую модель:
      - name, description
      - period_start / period_end
      - tags: list[str] (JSONB)
      - kind: ProjectKind
      - weight: int (по умолчанию 50)
      - repo_url / demo_url: Optional[str]
    """
    proj = get_one(session, Project, company_id=company.id, name="АЛОР БРОКЕР")

    target = {
        "description": (
            "Сервис для физических и юридических лиц, осуществляющих финансовые операции с "
            "ценными бумагами на нескольких российских биржах. На проекте разработан сервис "
            "нотификации, внесены существенные доработки в сервис регистрации клиентов и "
            "выполнена интеграция сервиса отправки отчётов в ФНС с внешним сервисом."
        ),
        "period_start": date(2024, 5, 13),
        "period_end": date(2024, 10, 27),
        "tags": ["fintech", "notifications"],
        "kind": ProjectKind.COMMERCIAL,
        "weight": 50,
        "repo_url": None,
        "demo_url": None,
    }

    if proj:
        changed = False
        for field, val in target.items():
            if getattr(proj, field) != val:
                setattr(proj, field, val)
                changed = True
        if changed:
            session.flush()
        return proj

    proj = Project(
        company_id=company.id,
        name="АЛОР БРОКЕР",
        **target,
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
            "Интеграция с Контур.Экстерн для отчётности в ФНС",
            "Выполнил интеграцию внутреннего сервиса по отправке отчётов в ФНС "
            "с внешним API Контур.Экстерна.",
            [],
        ),
        (
            "Сервис нотификаций для бэк-офиса и клиентов",
            "Разработал сервис по отправке уведомлений на e-mail сотрудникам бэк-офиса "
            "и клиентам об изменениях по ключам доступа к сервису.",
            [],
        ),
        (
            "Доработка сервиса регистрации клиентов",
            "Перестроил архитектуру, добавил модуль валидации клиентских данных перед "
            "отправкой на биржу.",
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
        ("Интеграция с Контур.Экстерн — схема", "https://example.org/alor-kontur-extern.pdf", "diagram"),
        ("Нотификации — дизайн и шаблоны писем", "https://example.org/alor-notify-spec.html", "spec"),
        ("Регистрация клиентов — валидация и поток данных", "https://example.org/alor-onboarding-validate.pdf", "diagram"),
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
            "Python 3.9", "FastAPI", "Pydantic", "SQLAlchemy", "Alembic",
            "asyncio", "Celery",
            # Интеграции/очереди
            "RabbitMQ",
            # Хранилище/инфра
            "PostgreSQL", "GitLab", "Docker",
        ])

        ensure_achievements(db, project)
        ensure_documents(db, project, company)

        db.commit()
        print("✅ Seed completed: ООО «АЛОР +» / АЛОР БРОКЕР")


if __name__ == "__main__":
    run()
