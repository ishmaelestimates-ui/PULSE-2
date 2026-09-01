"""initial schema: episodes and editorial_reviews

Revision ID: 0001
Revises:
Create Date: 2026-08-22

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.db_compat import pg_enum, enum_compat, create_enum_if_pg, drop_enum_if_pg, JSONB_COMPAT

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


decision_type_enum = pg_enum(
    "strong_moment",
    "weak_section",
    "clip_candidate",
    "opening",
    "closing",
    name="decision_type_enum",
)

review_status_enum = pg_enum(
    "recommended",
    "accepted",
    "rejected",
    "unresolved",
    name="review_status_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    create_enum_if_pg(decision_type_enum, bind)
    create_enum_if_pg(review_status_enum, bind)

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("analysis", JSONB_COMPAT, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "editorial_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("decision_type", enum_compat(decision_type_enum), nullable=False),
        sa.Column("decision_reference", JSONB_COMPAT, nullable=False),
        sa.Column(
            "status",
            enum_compat(review_status_enum),
            nullable=False,
            server_default="recommended",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("editorial_reviews")
    op.drop_table("episodes")
    drop_enum_if_pg(review_status_enum, op.get_bind())
    drop_enum_if_pg(decision_type_enum, op.get_bind())
