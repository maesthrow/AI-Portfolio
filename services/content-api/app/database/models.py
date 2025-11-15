from datetime import datetime, date
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Integer, String, Text, Date, TIMESTAMP, ForeignKey, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )

    # passive_deletes=True позволяет SQLAlchemy не грузить детей при DELETE,
    # полагаясь на FK ON DELETE SET NULL.
    projects: Mapped[list["Project"]] = relationship(
        back_populates="company",
        passive_deletes=True,
        # (опционально) зададим дефолтную сортировку списка проектов компании
        order_by="(Project.kind, Project.weight.desc(), Project.period_start.desc().nullslast())",
    )


class ProjectTechnology(Base):
    __tablename__ = "project_technologies"
    __table_args__ = (
        UniqueConstraint("project_id", "technology_id", name="uq_project_technology"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    technology_id: Mapped[int] = mapped_column(
        ForeignKey("technologies.id", ondelete="CASCADE"), index=True, nullable=False
    )


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    projects: Mapped[List["Project"]] = relationship(
        secondary="project_technologies", back_populates="technologies"
    )


class ProjectKind(str, Enum):
    COMMERCIAL = "commercial"
    PERSONAL = "personal"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Для личных проектов компания отсутствует => допускаем NULL.
    # На удаление компании — делаем SET NULL, чтобы карточки не пропадали.
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    period_start: Mapped[Optional[date]] = mapped_column(Date)
    period_end: Mapped[Optional[date]] = mapped_column(Date)

    # Тип проекта: коммерческий/личный
    kind: Mapped[ProjectKind] = mapped_column(
        SAEnum(ProjectKind, name="project_kind"),
        nullable=False,
        default=ProjectKind.COMMERCIAL,
    )

    # Ручной вес для сортировки внутри группы (чем больше — тем выше)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Опциональные ссылки — удобно для личных проектов
    repo_url: Mapped[Optional[str]] = mapped_column(String(255))
    demo_url: Mapped[Optional[str]] = mapped_column(String(255))

    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # --- relationships ---
    company: Mapped[Optional["Company"]] = relationship(
        back_populates="projects",
        passive_deletes=True,  # чтобы SET NULL отработал без лишних запросов
    )

    achievements: Mapped[list["Achievement"]] = relationship(
        back_populates="project",
        cascade="all,delete-orphan",
    )

    documents: Mapped[list["Document"]] = relationship(
        back_populates="project",
        cascade="all,delete-orphan",
    )

    technologies: Mapped[List["Technology"]] = relationship(
        secondary="project_technologies",
        back_populates="projects",
    )


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    links: Mapped[list[str]] = mapped_column(JSONB, default=list)

    project: Mapped["Project"] = relationship(back_populates="achievements")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    doc_type: Mapped[Optional[str]] = mapped_column(String(50))
    project_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), index=True
    )
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), index=True
    )
    meta: Mapped[dict | None] = mapped_column(JSONB)

    project: Mapped[Optional["Project"]] = relationship(back_populates="documents")
