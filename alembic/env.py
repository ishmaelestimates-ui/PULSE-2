"""
Alembic environment file. Pulls the database URL from application
settings (i.e. the DATABASE_URL environment variable) rather than a
hardcoded value in alembic.ini, and points autogenerate at the app's
declarative Base so `alembic revision --autogenerate` picks up model
changes.
"""
import time
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.exc import OperationalError

from app.config import get_settings
from app.database import Base
from app.models import (  # noqa: F401 - ensure models are registered
    ActivityLogEntry,
    AuditLog,
    AutoSave,
    BrandSettings,
    BudgetItem,
    CampaignPack,
    ColorGrade,
    CompetitorBenchmark,
    Coverage,
    CulturalFootprintItem,
    EditorialReview,
    Embargo,
    Episode,
    FameScoreSnapshot,
    FestivalMatch,
    FilmAct,
    Invite,
    JournalistLead,
    MagicLinkToken,
    MediaFile,
    Mention,
    ProjectMilestone,
    RedditComment,
    RedditKarma,
    RedditPost,
    RedditCommunitySnapshot,
    RedditOpportunity,
    ScheduledPost,
    PressKit,
    TerritoryRelease,
    TrailerCut,
    User,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# Migrations run multi-statement DDL inside a single transaction; a
# transaction-mode pooler in front of DATABASE_URL can drop that session
# mid-migration. Use the direct (non-pooled) URL for this step when one
# is configured, and fall back to DATABASE_URL otherwise so nothing
# breaks for setups that don't sit behind a pooler.
config.set_main_option(
    "sqlalchemy.url",
    settings.direct_database_url or settings.database_url,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        pool_pre_ping=True,
    )

    # Managed Postgres (Render and similar) occasionally drops a
    # freshly-opened connection's SSL session before the first query
    # completes, most often right after a deploy while the database is
    # waking up. That's a transient infrastructure hiccup, not a schema
    # or migration-logic problem, so a short bounded retry here is safe:
    # it does not touch what the migrations do, and it still fails loudly
    # (re-raising the real error) if the database is genuinely
    # unreachable rather than just slow to accept the first connection.
    max_attempts = 5
    backoff_seconds = 2

    for attempt in range(1, max_attempts + 1):
        try:
            with connectable.connect() as connection:
                context.configure(connection=connection, target_metadata=target_metadata)

                with context.begin_transaction():
                    context.run_migrations()
            break
        except OperationalError:
            if attempt == max_attempts:
                raise
            time.sleep(backoff_seconds * attempt)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
