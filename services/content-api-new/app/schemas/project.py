from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    id: int
    name: str
    slug: str
    description_md: str | None = None
    period: str | None = None
    company_name: str | None = None
    company_website: str | None = None
    domain: str | None = None
    featured: bool
    repo_url: str | None = None
    demo_url: str | None = None
    technologies: list[str] = []

    model_config = ConfigDict(from_attributes=True)
