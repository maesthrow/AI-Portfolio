from pydantic import BaseModel, ConfigDict


class FocusAreaBulletOut(BaseModel):
    id: int
    text: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class FocusAreaOut(BaseModel):
    id: int
    title: str
    is_primary: bool
    order_index: int
    bullets: list[FocusAreaBulletOut] = []

    model_config = ConfigDict(from_attributes=True)
