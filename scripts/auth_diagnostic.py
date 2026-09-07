"""Print safe production authentication status booleans.

Run from the application container only. This intentionally never prints
credential values, hashes, connection strings, or tokens.
"""
from app.database import SessionLocal
from app.services.auth_service import get_safe_bootstrap_status


def main() -> None:
    db = SessionLocal()
    try:
        print(get_safe_bootstrap_status(db))
    finally:
        db.close()


if __name__ == "__main__":
    main()
