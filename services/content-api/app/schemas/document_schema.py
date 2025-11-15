from pydantic import BaseModel
from typing import Optional


class DocumentOut(BaseModel):
    title: str
    url: str
    doc_type: Optional[str] = None
