from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.profile import Profile
from app.schemas.profile import ProfileOut

router = APIRouter()


@router.get("/", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    stmt = select(Profile).order_by(Profile.id.asc()).limit(1)
    profile = db.execute(stmt).scalars().first()
    if not profile:
        raise ValueError("Profile is not populated yet")
    return profile
