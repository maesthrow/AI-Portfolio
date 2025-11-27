from datetime import date

from pydantic import BaseModel, ConfigDict


class ExperienceOut(BaseModel):
    id: int
    role: str
    company_name: str
    company_url: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool
    kind: str
    description_md: str
    order_index: int

    model_config = ConfigDict(from_attributes=True)
