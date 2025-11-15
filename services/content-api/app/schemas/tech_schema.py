# services/content-api/app/schemas.py
from pydantic import BaseModel


class TechnologyOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True  # позволяет .model_validate из ORM
