# services/content-api/app/seed/seed_hyper_keeper.py
from __future__ import annotations

from datetime import date
from typing import Iterable

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.settings import settings
from app.database.models import (
    Project, Document, Achievement,
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


def ensure_project(session) -> Project:
    """
    ЛИЧНЫЙ проект (company_id = NULL).
    Поля проекта соответствуют новой модели: kind, weight, repo_url, demo_url.
    """
    proj = get_one(session, Project, company_id=None, name="HyperKeeper")
    if proj:
        return proj

    proj = Project(
        company_id=None,
        kind=ProjectKind.PERSONAL,
        weight=50,  # базовый вес; дальше можно тонко настраивать
        name="HyperKeeper",
        description=(
            "Telegram-бот для личного хранилища: структуры папок, файлы, медиа и заметки. "
            "Поддерживает быструю навигацию, поиск и управление контентом. "
            "Есть интеграция с LLM с сохранением истории диалогов."
        ),
        # ориентир по памяти: старт ~ 2025-08-11; без даты окончания (активный личный проект)
        period_start=date(2023, 12, 28),
        period_end=None,
        # репозиторий/демо можно будет дописать позднее
        repo_url="https://github.com/maesthrow/HyperKeeperBot",
        demo_url="https://t.me/HyperKeeperBot",
        tags=["telegram", "storage", "llm", "gigachat"],
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
    """
    links — jsonb-массив строк (ссылки на демо/превью/заметки). Можно заполнять позже.
    """
    items: Iterable[tuple[str, str, list[str]]] = [
        (
            "Личное хранилище в Telegram",
            "Реализовал бота с поддержкой папок, загрузки файлов/медиа и быстрых операций "
            "над контентом.",
            []
        ),
        (
            "Интеграция LLM",
            "Создал модуль для общения с языковой моделью GigaChat. "
            "Реализовал возможность вести несколько чатов с сохранением истории и возможностью продолжать диалоги.",
            []
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


def ensure_documents(session, project: Project) -> None:
    """
    Черновые документы — заменишь на реальные ссылки, когда будут готовы.
    """
    docs = [
        ("Архитектура HyperKeeper", "https://example.org/hyperkeeper-arch.pdf", "diagram"),
        ("Схемы API мини-приложения", "https://example.org/hyperkeeper-miniapp-api.pdf", "spec"),
    ]
    for title, url, doc_type in docs:
        if not get_one(session, Document, title=title):
            session.add(Document(
                title=title,
                url=url,
                doc_type=doc_type,
                project_id=project.id,
                company_id=None,
                meta={"seed": True},
            ))


def run():
    with SessionLocal() as db:
        project = ensure_project(db)

        ensure_project_techs(db, project, [
            # Язык/фреймворки
            "Python 3.12", "aiogram", "aiogram-dialog",
            # Хранилища/поиск
            "MongoDB",
            # LLM
            "LangChain", "GigaChain",
            # Инфраструктура
            "Docker",
        ])

        ensure_achievements(db, project)
        ensure_documents(db, project)

        db.commit()
        print("✅ Seed completed: PERSONAL / HyperKeeper")


if __name__ == "__main__":
    run()
