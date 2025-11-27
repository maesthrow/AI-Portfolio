from pydantic import BaseModel, ConfigDict


class ProfileOut(BaseModel):
    id: int
    full_name: str
    title: str
    subtitle: str | None = None
    location: str | None = None
    status: str | None = None
    avatar_url: str | None = None
    summary_md: str | None = None

    model_config = ConfigDict(from_attributes=True)
