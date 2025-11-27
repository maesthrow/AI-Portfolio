from pydantic import BaseModel, ConfigDict


class PublicationOut(BaseModel):
    id: int
    title: str
    year: int
    source: str
    url: str
    badge: str | None = None
    description_md: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)
