from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class FocusArea(Base):
    __tablename__ = "focus_area"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    bullets: Mapped[list["FocusAreaBullet"]] = relationship(
        "FocusAreaBullet", back_populates="focus_area", cascade="all, delete-orphan"
    )


class FocusAreaBullet(Base):
    __tablename__ = "focus_area_bullet"

    id: Mapped[int] = mapped_column(primary_key=True)
    focus_area_id: Mapped[int] = mapped_column(ForeignKey("focus_area.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    focus_area: Mapped[FocusArea] = relationship("FocusArea", back_populates="bullets")
