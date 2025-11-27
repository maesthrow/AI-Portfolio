from pydantic import BaseModel, ConfigDict


class TechnologyOut(BaseModel):
    id: int
    name: str
    slug: str
    category: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)
