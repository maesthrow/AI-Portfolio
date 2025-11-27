from pydantic import BaseModel, ConfigDict


class TechFocusTagOut(BaseModel):
    id: int
    name: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class TechFocusOut(BaseModel):
    id: int
    label: str
    description: str | None = None
    order_index: int
    tags: list[TechFocusTagOut] = []

    model_config = ConfigDict(from_attributes=True)
