from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.section_meta import SectionMeta
from app.schemas.section_meta import SectionMetaOut

router = APIRouter()


@router.get("/", response_model=list[SectionMetaOut])
def list_section_meta(db: Session = Depends(get_db)):
    stmt = select(SectionMeta).order_by(SectionMeta.section_key.asc())
    items = db.execute(stmt).scalars().all()
    return items


@router.get("/{section_key}", response_model=SectionMetaOut)
def get_section_meta(section_key: str, db: Session = Depends(get_db)):
    stmt = select(SectionMeta).where(SectionMeta.section_key == section_key)
    item = db.execute(stmt).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Section meta not found")
    return item
