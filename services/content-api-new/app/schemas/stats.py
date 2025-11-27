from pydantic import BaseModel, ConfigDict


class StatOut(BaseModel):
    id: int
    key: str
    label: str
    value: str
    hint: str | None = None
    group_name: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)
