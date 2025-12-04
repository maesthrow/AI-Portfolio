from pydantic import BaseModel, ConfigDict


class WorkApproachBulletOut(BaseModel):
    id: int
    text: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class WorkApproachOut(BaseModel):
    id: int
    title: str
    order_index: int
    bullets: list[WorkApproachBulletOut] = []

    model_config = ConfigDict(from_attributes=True)
