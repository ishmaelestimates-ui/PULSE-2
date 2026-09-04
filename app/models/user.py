"""
User management models.

Honesty notes:
  - Magic-link emails are NOT actually sent — there's no email-provider
    integration in this app (same "mock/placeholder" pattern as the PR
    module's pitch-sending). In development, the link is returned
    directly in the API response; in any other environment it's only
    logged server-side, and the request endpoint always returns a
    generic response regardless of whether the email exists, to avoid
    leaking account existence.
  - Session tokens are stateless (HS256, see auth_service.py) — there is
    no server-side revocation list, so "logout" is client-side only
    (discard the token). A stolen token remains valid until it expires.
  - The private application API is now protected at router registration
    time in app.main. Fine-grained role authorization is still evolving.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Nullable: a user created via invite might only ever use magic-link
    # login and never set a password.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role_enum", values_callable=lambda x: [e.value for e in x]), default=UserRole.EDITOR, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    activity: Mapped[list["ActivityLogEntry"]] = relationship(
        "ActivityLogEntry", back_populates="user", cascade="all, delete-orphan"
    )


class InviteStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="invite_role_enum"), default=UserRole.EDITOR, nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    status: Mapped[InviteStatus] = mapped_column(
        Enum(InviteStatus, name="invite_status_enum"), default=InviteStatus.PENDING, nullable=False
    )
    invited_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class MagicLinkToken(Base):
    __tablename__ = "magic_link_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ActivityLogEntry(Base):
    """Actions taken through authenticated endpoints. Historical data from
    pre-auth versions naturally has no user attribution."""

    __tablename__ = "activity_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "login", "invite_sent"
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="activity")
