from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.stats import Stat
from app.schemas.stats import StatOut

router = APIRouter()


@router.get("/", response_model=list[StatOut])
def list_stats(db: Session = Depends(get_db)):
    stmt = select(Stat).order_by(Stat.order_index.asc(), Stat.id.asc())
    return db.execute(stmt).scalars().all()
