from pydantic import BaseModel, ConfigDict


class HeroTagOut(BaseModel):
    id: int
    name: str
    url: str | None = None
    icon: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)
