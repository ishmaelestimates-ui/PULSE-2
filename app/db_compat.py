"""
Cross-dialect compatibility helpers.

Production runs on PostgreSQL (Render); local/dev testing can use SQLite,
which doesn't support Postgres-only constructs (JSONB, native ENUM types
with CREATE TYPE). Rather than scatter `.with_variant(...)` calls and
dialect checks across every model and migration, they're centralized
here.

Trade-off, stated plainly: on SQLite, ENUM columns fall back to a plain
VARCHAR with no CHECK constraint, so invalid values aren't rejected at
the database layer the way they are on real Postgres. That's an accepted
gap for local/dev testing, not something you'd want in production —
production should always run against Postgres, where the real
constraint applies.
"""
from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import ENUM, JSONB

# Real JSONB (indexing/operator support) on Postgres; falls back to the
# generic JSON type on SQLite, which has no native JSONB.
JSONB_COMPAT = JSONB().with_variant(JSON(), "sqlite")


def pg_enum(*values: str, name: str) -> ENUM:
    """A Postgres ENUM type object. Use `enum_compat()` for the actual
    column type (adds the SQLite fallback) and `create_enum_if_pg` /
    `drop_enum_if_pg` for the explicit CREATE TYPE / DROP TYPE migration
    calls, which are only valid against Postgres."""
    return ENUM(*values, name=name, create_type=False)


def enum_compat(enum_type: ENUM, length: int = 50):
    """Column-type wrapper: the real Postgres ENUM on Postgres, a plain
    VARCHAR on SQLite (see module docstring for the trade-off)."""
    return enum_type.with_variant(String(length=length), "sqlite")


def create_enum_if_pg(enum_type: ENUM, bind) -> None:
    if bind.dialect.name == "postgresql":
        enum_type.create(bind, checkfirst=True)


def drop_enum_if_pg(enum_type: ENUM, bind) -> None:
    if bind.dialect.name == "postgresql":
        enum_type.drop(bind, checkfirst=True)
