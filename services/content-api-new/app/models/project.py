from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin
from app.models.technology import Technology


class Project(TimestampMixin, Base):
    __tablename__ = "project"
    __table_args__ = (UniqueConstraint("slug", name="uq_project_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    short_title: Mapped[str | None] = mapped_column(String, nullable=True)
    description_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_description_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    period: Mapped[str | None] = mapped_column(String, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String, nullable=True)
    company_website: Mapped[str | None] = mapped_column(String, nullable=True)
    domain: Mapped[str | None] = mapped_column(String, nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    repo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    demo_url: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    technologies: Mapped[list[Technology]] = relationship(
        secondary="project_technology",
        back_populates="projects",
        order_by="Technology.order_index.asc()",
    )


class ProjectTechnology(Base):
    __tablename__ = "project_technology"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), primary_key=True
    )
    technology_id: Mapped[int] = mapped_column(
        ForeignKey("technology.id", ondelete="CASCADE"), primary_key=True
    )


Technology.projects = relationship(
    "Project",
    secondary="project_technology",
    back_populates="technologies",
)
