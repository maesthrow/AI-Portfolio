from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileExport(BaseModel):
    id: int
    full_name: str
    title: str
    subtitle: str | None = None
    summary_md: str | None = None
    hero_headline: str | None = None
    hero_description: str | None = None
    current_position: str | None = None

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class ExperienceProjectExport(BaseModel):
    id: int
    experience_id: int | None = None
    name: str
    slug: str | None = None
    period: str | None = None
    description_md: str | None = None
    achievements_md: str | None = None
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class CompanyExperienceExport(BaseModel):
    id: int
    role: str
    company_name: str | None = None
    company_slug: str | None = None
    company_url: str | None = None
    company_summary_md: str | None = None
    company_role_md: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    kind: str | None = None
    summary_md: str | None = None
    achievements_md: str | None = None
    order_index: int = 0
    projects: list[ExperienceProjectExport] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class ProjectExport(BaseModel):
    id: int
    name: str
    slug: str
    featured: bool
    domain: str | None = None
    repo_url: str | None = None
    demo_url: str | None = None
    description_md: str | None = None
    long_description_md: str | None = None
    period: str | None = None
    company_name: str | None = None
    company_website: str | None = None
    technologies: list[str] = Field(default_factory=list)
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")

    @field_validator("technologies", mode="before")
    @classmethod
    def _coerce_technologies(cls, v):
        if v is None:
            return []
        items = v if isinstance(v, (list, tuple)) else [v]
        out: list[str] = []
        for item in items:
            if isinstance(item, str):
                out.append(item)
            elif hasattr(item, "name"):
                out.append(str(getattr(item, "name")))
            else:
                out.append(str(item))
        return out


class TechnologyExport(BaseModel):
    id: int
    name: str
    slug: str
    category: str | None = None
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class PublicationExport(BaseModel):
    id: int
    title: str
    year: int
    source: str
    url: str
    badge: str | None = None
    description_md: str | None = None
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class FocusAreaBulletExport(BaseModel):
    id: int
    text: str
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class FocusAreaExport(BaseModel):
    id: int
    title: str
    is_primary: bool
    order_index: int = 0
    bullets: list[FocusAreaBulletExport] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class WorkApproachBulletExport(BaseModel):
    id: int
    text: str
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class WorkApproachExport(BaseModel):
    id: int
    title: str
    icon: str | None = None
    order_index: int = 0
    bullets: list[WorkApproachBulletExport] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class TechFocusTagExport(BaseModel):
    id: int
    name: str
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class TechFocusExport(BaseModel):
    id: int
    label: str
    description: str | None = None
    order_index: int = 0
    tags: list[TechFocusTagExport] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class StatExport(BaseModel):
    id: int
    key: str
    label: str
    value: str
    hint: str | None = None
    group_name: str | None = None
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class ContactExport(BaseModel):
    id: int
    kind: str
    label: str
    value: str
    url: str
    is_primary: bool = False
    order_index: int = 0

    model_config = ConfigDict(from_attributes=True, extra="ignore")


class ExportPayload(BaseModel):
    profile: ProfileExport | None = None
    experiences: list[CompanyExperienceExport]
    projects: list[ProjectExport]
    technologies: list[TechnologyExport]
    publications: list[PublicationExport] = Field(default_factory=list)
    focus_areas: list[FocusAreaExport] = Field(default_factory=list)
    work_approaches: list[WorkApproachExport] = Field(default_factory=list)
    tech_focus: list[TechFocusExport] = Field(default_factory=list)
    stats: list[StatExport] = Field(default_factory=list)
    contacts: list[ContactExport] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")
