from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_id: int | None
    action: str
    method: str | None
    route: str | None
    status_code: int | None
    resource_type: str | None
    resource_id: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime

    class Config:
        from_attributes = True
