from pydantic import BaseModel, Field
from typing import List, Optional


class AchievementOut(BaseModel):
    title: str
    description: Optional[str] = None
    links: List[str] = Field(default_factory=list)
