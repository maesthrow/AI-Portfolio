from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.focus_area import FocusArea
from app.schemas.focus_area import FocusAreaOut

router = APIRouter()


@router.get("/", response_model=list[FocusAreaOut])
def list_focus_areas(db: Session = Depends(get_db)):
    stmt = (
        select(FocusArea)
        .options(joinedload(FocusArea.bullets))
        .order_by(FocusArea.order_index.asc(), FocusArea.id.asc())
    )
    items = db.execute(stmt).scalars().unique().all()
    for item in items:
        item.bullets.sort(key=lambda b: (b.order_index, b.id))
    return items
