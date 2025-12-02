from datetime import date

from pydantic import BaseModel, ConfigDict


class ExperienceOut(BaseModel):
    id: int
    role: str
    company_name: str | None = None
    company_url: str | None = None
    project_name: str | None = None
    project_slug: str | None = None
    project_url: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool
    kind: str
    summary_md: str | None = None
    achievements_md: str | None = None
    # Deprecated: legacy field kept for backward compatibility; avoid using in new clients.
    description_md: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)
