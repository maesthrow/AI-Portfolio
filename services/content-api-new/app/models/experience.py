from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class CompanyExperience(TimestampMixin, Base):
    __tablename__ = "experience"
    __table_args__ = (UniqueConstraint("company_slug", name="uq_experience_company_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String, nullable=True)
    company_url: Mapped[str | None] = mapped_column(String, nullable=True)
    company_slug: Mapped[str] = mapped_column(String, nullable=False)
    company_summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_role_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kind: Mapped[str] = mapped_column(String, nullable=False)
    description_md: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Deprecated: legacy field; to be removed after migration of data.",
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    project_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    project_slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    summary_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    achievements_md: Mapped[str | None] = mapped_column(Text, nullable=True)


# Backward compatibility for old imports
Experience = CompanyExperience
