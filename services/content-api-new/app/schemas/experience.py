from datetime import date

from pydantic import BaseModel, ConfigDict


class CompanyExperienceOut(BaseModel):
    id: int
    company_slug: str
    company_name: str | None = None
    company_url: str | None = None
    role: str
    start_date: date
    end_date: date | None = None
    is_current: bool
    kind: str
    company_summary_md: str | None = None
    company_role_md: str | None = None
    order_index: int

    model_config = ConfigDict(from_attributes=True)


class ExperienceProjectOut(BaseModel):
    id: int
    name: str
    slug: str | None = None
    period: str | None = None
    description_md: str | None = None
    achievements_md: str | None = None
    order_index: int
    technologies: list[str] = []

    model_config = ConfigDict(from_attributes=True)


class CompanyExperienceDetail(BaseModel):
    company: CompanyExperienceOut
    projects: list[ExperienceProjectOut]
