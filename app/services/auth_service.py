"""
Auth core: password hashing, session tokens, invite/magic-link tokens.

Password hashing uses Python's stdlib `hashlib.pbkdf2_hmac` (PBKDF2-
HMAC-SHA256, 600k iterations per current OWASP guidance) rather than
passlib/bcrypt, specifically to avoid a native-extension dependency in an
environment where installs can't be verified against a live network —
PBKDF2 via hashlib is a legitimate, documented secure choice and needs
nothing beyond the standard library.

Session tokens are signed JWTs (HS256, via PyJWT) using SECRET_KEY.
They're stateless: there's no server-side revocation list, so a token
remains valid until it expires regardless of "logout." See
app/models/user.py for the magic-link email caveat.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

_PBKDF2_ITERATIONS = 600_000
_PBKDF2_ALGO = "sha256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO,
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo_tag, iterations_str, salt_hex, derived_hex = stored_hash.split("$")
        if algo_tag != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(derived_hex)
    except (ValueError, AttributeError):
        return False

    candidate = hashlib.pbkdf2_hmac(
        _PBKDF2_ALGO,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate, expected)


def create_session_token(user_id: int, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(hours=settings.session_token_ttl_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_session_token(token: str) -> dict | None:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def generate_magic_link_token() -> str:
    return secrets.token_urlsafe(32)


def bootstrap_admin_if_needed(db) -> None:
    """Creates or repairs the configured bootstrap admin at app startup.

    When BOOTSTRAP_ADMIN_PASSWORD is set, the configured email is made an
    active admin with that password. This also repairs an existing bootstrap
    account if the database was initialized before bootstrap credentials
    were configured.
    """
    import logging

    from app.models.user import User, UserRole

    logger = logging.getLogger(__name__)
    settings = get_settings()

    email = settings.bootstrap_admin_email
    configured_password = settings.bootstrap_admin_password

    if configured_password:
        admin = db.query(User).filter(User.email == email).first()

        if admin is None:
            admin = User(
                email=email,
                name="Admin",
                role=UserRole.ADMIN,
                password_hash=hash_password(configured_password),
                is_active=True,
            )
            db.add(admin)
            db.commit()
            logger.info("Bootstrapped configured admin user %s.", email)
            return

        needs_update = (
            not admin.password_hash
            or not verify_password(configured_password, admin.password_hash)
            or admin.role != UserRole.ADMIN
            or not admin.is_active
        )

        if needs_update:
            admin.password_hash = hash_password(configured_password)
            admin.role = UserRole.ADMIN
            admin.is_active = True
            db.add(admin)
            db.commit()
            logger.info("Repaired configured bootstrap admin user %s.", email)

        return

    if db.query(User).count() > 0:
        return

    password = secrets.token_urlsafe(12)
    admin = User(
        email=email,
        name="Admin",
        role=UserRole.ADMIN,
        password_hash=hash_password(password),
    )
    db.add(admin)
    db.commit()

    logger.warning(
        "Bootstrapped first admin user %s with a GENERATED password: %s "
        "— this is printed ONCE and not recoverable. Set "
        "BOOTSTRAP_ADMIN_PASSWORD before first run.",
        email,
        password,
    )
