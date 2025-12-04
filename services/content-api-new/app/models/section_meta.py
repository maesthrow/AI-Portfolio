from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class SectionMeta(Base):
    __tablename__ = "section_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    section_key: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)
