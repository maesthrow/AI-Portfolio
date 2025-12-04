from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class WorkApproach(Base):
    __tablename__ = "work_approach"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    bullets: Mapped[list["WorkApproachBullet"]] = relationship(
        "WorkApproachBullet", back_populates="work_approach", cascade="all, delete-orphan"
    )


class WorkApproachBullet(Base):
    __tablename__ = "work_approach_bullet"

    id: Mapped[int] = mapped_column(primary_key=True)
    work_approach_id: Mapped[int] = mapped_column(ForeignKey("work_approach.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    work_approach: Mapped[WorkApproach] = relationship("WorkApproach", back_populates="bullets")
