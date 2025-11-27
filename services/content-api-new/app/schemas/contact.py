from pydantic import BaseModel, ConfigDict


class ContactOut(BaseModel):
    id: int
    kind: str
    label: str
    value: str
    url: str
    order_index: int
    is_primary: bool

    model_config = ConfigDict(from_attributes=True)
