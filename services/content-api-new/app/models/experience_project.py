from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, TimestampMixin


class ExperienceProject(TimestampMixin, Base):
    __tablename__ = "experience_project"
    __table_args__ = (
        UniqueConstraint("experience_id", "slug", name="uq_experience_project_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    experience_id: Mapped[int] = mapped_column(
        ForeignKey("experience.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False)
    period: Mapped[str | None] = mapped_column(String, nullable=True)
    description_md: Mapped[str] = mapped_column(Text, nullable=False)
    achievements_md: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    company = relationship(
        "CompanyExperience",
        back_populates="projects",
    )
