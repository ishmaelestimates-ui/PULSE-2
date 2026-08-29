"""
Auth endpoints: invite-only signup, password login, magic-link login.

See app/models/user.py for the magic-link email caveat (not actually
sent — dev mode returns the link directly; other environments only log
it) and app/services/auth_service.py for the hashing/token approach.
"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.config import get_settings
from app.database import get_db
from app.models.user import ActivityLogEntry, Invite, InviteStatus, MagicLinkToken, User
from app.schemas.user import (
    AcceptInviteRequest,
    InviteCreate,
    InviteOut,
    LoginRequest,
    MagicLinkRequest,
    MagicLinkRequestResponse,
    MagicLinkVerifyRequest,
    TokenResponse,
    UserOut,
)
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _log_activity(db: Session, user_id: int, action: str, detail: str | None = None):
    db.add(ActivityLogEntry(user_id=user_id, action=action, detail=detail))


@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def create_invite(payload: InviteCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    settings = get_settings()

    existing_user = db.query(User).filter(User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That email already has an account.")

    active_user_count = db.query(User).filter(User.is_active.is_(True)).count()
    pending_invite_count = db.query(Invite).filter(Invite.status == InviteStatus.PENDING).count()
    if active_user_count + pending_invite_count >= settings.max_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User limit reached ({settings.max_users}). Deactivate a user or revoke a pending invite first.",
        )

    invite = Invite(
        email=payload.email,
        role=payload.role,
        token=auth_service.generate_invite_token(),
        invited_by_user_id=admin.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.invite_ttl_days),
    )
    db.add(invite)
    _log_activity(db, admin.id, "invite_sent", detail=payload.email)
    db.commit()
    db.refresh(invite)

    out = InviteOut.model_validate(invite)
    if settings.environment == "development":
        out.magic_link_url = f"/accept-invite?token={invite.token}"
    else:
        logger.info("Invite created for %s — link not emailed (no email provider configured).", payload.email)
    return out


@router.get("/invites", response_model=list[InviteOut])
def list_invites(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    return db.query(Invite).order_by(Invite.created_at.desc()).all()


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(invite_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    invite = db.query(Invite).filter(Invite.id == invite_id).first()
    if invite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invite not found.")
    invite.status = InviteStatus.REVOKED
    db.add(invite)
    db.commit()


@router.post("/accept-invite", response_model=TokenResponse)
def accept_invite(payload: AcceptInviteRequest, db: Session = Depends(get_db)):
    invite = db.query(Invite).filter(Invite.token == payload.token).first()
    if invite is None or invite.status != InviteStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already-used invite.")
    if invite.expires_at < datetime.now(timezone.utc):
        invite.status = InviteStatus.EXPIRED
        db.add(invite)
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invite has expired.")

    user = User(
        email=invite.email,
        name=payload.name,
        role=invite.role,
        password_hash=auth_service.hash_password(payload.password) if payload.password else None,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    invite.status = InviteStatus.ACCEPTED
    db.add(invite)
    db.flush()
    _log_activity(db, user.id, "invite_accepted")
    db.commit()
    db.refresh(user)

    token = auth_service.create_session_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user is None or not user.is_active or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    if not auth_service.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")

    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    _log_activity(db, user.id, "login", detail="password")
    db.commit()
    db.refresh(user)

    token = auth_service.create_session_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=user)


@router.post("/magic-link/request", response_model=MagicLinkRequestResponse)
def request_magic_link(payload: MagicLinkRequest, db: Session = Depends(get_db)):
    settings = get_settings()
    user = db.query(User).filter(User.email == payload.email, User.is_active.is_(True)).first()

    # Always return the same generic message whether or not the email
    # exists, so this endpoint can't be used to enumerate accounts.
    response = MagicLinkRequestResponse()
    if user is None:
        return response

    link_token = auth_service.generate_magic_link_token()
    db.add(
        MagicLinkToken(
            user_id=user.id,
            token=link_token,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=settings.magic_link_ttl_minutes),
        )
    )
    db.commit()

    if settings.environment == "development":
        response.dev_link = f"/magic-link?token={link_token}"
    else:
        logger.info("Magic link requested for user %s — not emailed (no email provider configured).", user.id)
    return response


@router.post("/magic-link/verify", response_model=TokenResponse)
def verify_magic_link(payload: MagicLinkVerifyRequest, db: Session = Depends(get_db)):
    link = db.query(MagicLinkToken).filter(MagicLinkToken.token == payload.token).first()
    if link is None or link.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already-used link.")
    if link.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This link has expired.")

    user = db.query(User).filter(User.id == link.user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or deactivated.")

    link.used_at = datetime.now(timezone.utc)
    user.last_login_at = datetime.now(timezone.utc)
    db.add_all([link, user])
    _log_activity(db, user.id, "login", detail="magic_link")
    db.commit()
    db.refresh(user)

    token = auth_service.create_session_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
def get_me(user: User = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    """Stateless tokens — this is a no-op server-side. Discard the token
    client-side; there is no revocation list."""
    return {"message": "Logged out client-side. Token remains technically valid until it expires."}
