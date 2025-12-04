from pydantic import BaseModel, ConfigDict


class SectionMetaOut(BaseModel):
    id: int
    section_key: str
    title: str | None = None
    subtitle: str | None = None

    model_config = ConfigDict(from_attributes=True)
