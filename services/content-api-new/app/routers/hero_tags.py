from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.hero_tag import HeroTag
from app.schemas.hero_tag import HeroTagOut

router = APIRouter()


@router.get("/", response_model=list[HeroTagOut])
def list_hero_tags(db: Session = Depends(get_db)):
    stmt = select(HeroTag).order_by(HeroTag.order_index.asc(), HeroTag.id.asc())
    items = db.execute(stmt).scalars().all()
    return items
