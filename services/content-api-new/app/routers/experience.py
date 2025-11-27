from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.experience import Experience
from app.schemas.experience import ExperienceOut

router = APIRouter()


@router.get("/", response_model=list[ExperienceOut])
def list_experience(db: Session = Depends(get_db)):
    stmt = select(Experience).order_by(Experience.order_index.asc(), Experience.start_date.desc())
    return db.execute(stmt).scalars().all()
