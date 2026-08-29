"""
Pydantic schemas for auth and user management.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import InviteStatus, UserRole


class InviteCreate(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.EDITOR


class InviteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: UserRole
    status: InviteStatus
    expires_at: datetime
    created_at: datetime
    magic_link_url: Optional[str] = None  # only populated in dev — see auth_service note


class AcceptInviteRequest(BaseModel):
    token: str
    name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkRequestResponse(BaseModel):
    message: str = "If that email is registered, a sign-in link has been sent."
    dev_link: Optional[str] = None  # only populated when ENVIRONMENT=development


class MagicLinkVerifyRequest(BaseModel):
    token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class ActivityLogEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    detail: Optional[str]
    created_at: datetime


class UserActivityResponse(BaseModel):
    user: UserOut
    activity: list[ActivityLogEntryOut]
