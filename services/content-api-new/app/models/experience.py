from datetime import date

from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, TimestampMixin


class Experience(TimestampMixin, Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str | None] = mapped_column(String, nullable=True)
    company_url: Mapped[str | None] = mapped_column(String, nullable=True)
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
