from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database.models import Technology
from .deps import get_db
from .schemas.tech_schema import TechnologyOut

router = APIRouter(tags=["technologies"])


@router.get("/technologies", response_model=List[TechnologyOut])
def list_technologies(
    q: Optional[str] = Query(None, description="Поиск по подстроке (ILIKE)"),
    db: Session = Depends(get_db),
):
    stmt = select(Technology).order_by(Technology.name.asc())
    if q:
        stmt = stmt.where(Technology.name.ilike(f"%{q}%"))
    rows = db.execute(stmt).scalars().all()
    return [TechnologyOut.model_validate(t) for t in rows]
