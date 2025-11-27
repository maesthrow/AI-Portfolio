from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.contact import Contact
from app.schemas.contact import ContactOut

router = APIRouter()


@router.get("/", response_model=list[ContactOut])
def list_contacts(db: Session = Depends(get_db)):
    stmt = select(Contact).order_by(Contact.order_index.asc(), Contact.id.asc())
    return db.execute(stmt).scalars().all()
