from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AutoSaveCreate(BaseModel):
    episode_id: int = Field(gt=0)
    data: dict[str, Any] = Field(default_factory=dict)


class AutoSaveOut(BaseModel):
    id: int
    episode_id: int
    saved_at: datetime
    data: dict[str, Any]

    class Config:
        from_attributes = True


class AutoSaveStatusOut(BaseModel):
    available: bool
    snapshot: AutoSaveOut | None = None
