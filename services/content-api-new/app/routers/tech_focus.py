from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.tech_focus import TechFocus
from app.schemas.tech_focus import TechFocusOut

router = APIRouter()


@router.get("/", response_model=list[TechFocusOut])
def list_tech_focus(db: Session = Depends(get_db)):
    stmt = (
        select(TechFocus)
        .options(joinedload(TechFocus.tags))
        .order_by(TechFocus.order_index.asc(), TechFocus.id.asc())
    )
    items = db.execute(stmt).scalars().unique().all()
    for item in items:
        item.tags.sort(key=lambda t: (t.order_index, t.id))
    return items
