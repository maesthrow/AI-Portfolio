from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.publication import Publication
from app.schemas.publication import PublicationOut

router = APIRouter()


@router.get("/", response_model=list[PublicationOut])
def list_publications(db: Session = Depends(get_db)):
    stmt = select(Publication).order_by(Publication.order_index.asc(), Publication.id.asc())
    return db.execute(stmt).scalars().all()
