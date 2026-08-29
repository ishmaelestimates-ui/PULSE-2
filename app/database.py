"""
SQLAlchemy engine, session factory, and declarative base.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

# `pool_pre_ping` avoids "server has gone away" errors on long-lived
# connections. `future=True` opts into SQLAlchemy 2.0 style behavior.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session and guarantees
    it is closed after the request finishes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
