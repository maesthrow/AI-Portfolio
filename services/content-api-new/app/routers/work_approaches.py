from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.models.work_approach import WorkApproach
from app.schemas.work_approach import WorkApproachOut

router = APIRouter()


@router.get("/", response_model=list[WorkApproachOut])
def list_work_approaches(db: Session = Depends(get_db)):
    stmt = (
        select(WorkApproach)
        .options(joinedload(WorkApproach.bullets))
        .order_by(WorkApproach.order_index.asc(), WorkApproach.id.asc())
    )
    items = db.execute(stmt).scalars().unique().all()
    for item in items:
        item.bullets.sort(key=lambda b: (b.order_index, b.id))
    return items
