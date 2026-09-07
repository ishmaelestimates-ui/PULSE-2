"""Print safe production authentication status booleans.

Run from the application container only. This intentionally never prints
credential values, hashes, connection strings, or tokens.
"""
from app.config import get_settings
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.services.auth_service import verify_password


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        bootstrap_user = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
        target_user = db.query(User).filter(User.email == "admin@example.com").first()
        password_configured = bool(settings.bootstrap_admin_password)

        print({
            "environment_production": settings.environment.lower() == "production",
            "bootstrap_email_configured": bool(settings.bootstrap_admin_email),
            "bootstrap_password_configured": password_configured,
            "bootstrap_user_exists": bootstrap_user is not None,
            "bootstrap_user_active": bool(bootstrap_user and bootstrap_user.is_active),
            "bootstrap_user_admin": bool(bootstrap_user and bootstrap_user.role == UserRole.ADMIN),
            "bootstrap_password_matches": bool(
                password_configured
                and bootstrap_user
                and bootstrap_user.password_hash
                and verify_password(settings.bootstrap_admin_password, bootstrap_user.password_hash)
            ),
            "target_admin_exists": target_user is not None,
            "target_admin_active": bool(target_user and target_user.is_active),
            "target_admin_has_password_hash": bool(target_user and target_user.password_hash),
        })
    finally:
        db.close()


if __name__ == "__main__":
    main()
