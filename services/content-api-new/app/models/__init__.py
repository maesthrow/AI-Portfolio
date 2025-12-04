from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# Import all models for Alembic autogenerate
from app.models.profile import Profile  # noqa: E402, F401
from app.models.contact import Contact  # noqa: E402, F401
from app.models.experience import CompanyExperience  # noqa: E402, F401
from app.models.experience_project import ExperienceProject  # noqa: E402, F401
from app.models.project import Project  # noqa: E402, F401
from app.models.publication import Publication  # noqa: E402, F401
from app.models.stats import Stat  # noqa: E402, F401
from app.models.tech_focus import TechFocus, TechFocusTag  # noqa: E402, F401
from app.models.technology import Technology  # noqa: E402, F401
from app.models.hero_tag import HeroTag  # noqa: E402, F401
from app.models.focus_area import FocusArea, FocusAreaBullet  # noqa: E402, F401
from app.models.work_approach import WorkApproach, WorkApproachBullet  # noqa: E402, F401
from app.models.section_meta import SectionMeta  # noqa: E402, F401


__all__ = [
    "Base",
    "TimestampMixin",
    "Profile",
    "Contact",
    "CompanyExperience",
    "ExperienceProject",
    "Project",
    "Publication",
    "Stat",
    "TechFocus",
    "TechFocusTag",
    "Technology",
    "HeroTag",
    "FocusArea",
    "FocusAreaBullet",
    "WorkApproach",
    "WorkApproachBullet",
    "SectionMeta",
]
