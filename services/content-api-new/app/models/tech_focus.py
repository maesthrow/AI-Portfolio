from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class TechFocus(Base):
    __tablename__ = "tech_focus"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tags: Mapped[list["TechFocusTag"]] = relationship(
        "TechFocusTag", back_populates="tech_focus", cascade="all, delete-orphan"
    )


class TechFocusTag(Base):
    __tablename__ = "tech_focus_tag"

    id: Mapped[int] = mapped_column(primary_key=True)
    tech_focus_id: Mapped[int] = mapped_column(ForeignKey("tech_focus.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tech_focus: Mapped[TechFocus] = relationship("TechFocus", back_populates="tags")
