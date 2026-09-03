"""initial schema: episodes and editorial_reviews

Revision ID: 0001
Revises:
Create Date: 2026-08-22

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


decision_type_enum = postgresql.ENUM(
    "strong_moment",
    "weak_section",
    "clip_candidate",
    "opening",
    "closing",
    name="decision_type_enum",
)
decision_type_enum.create_type = False

review_status_enum = postgresql.ENUM(
    "recommended",
    "accepted",
    "rejected",
    "unresolved",
    name="review_status_enum",
)
review_status_enum.create_type = False


def upgrade() -> None:
    bind = op.get_bind()
    decision_type_enum.create(bind, checkfirst=True)
    review_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "episodes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("analysis", postgresql.JSONB(), nullable=True),
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
        sa.Column("decision_type", decision_type_enum, nullable=False),
        sa.Column("decision_reference", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            review_status_enum,
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
    review_status_enum.drop(op.get_bind(), checkfirst=True)
    decision_type_enum.drop(op.get_bind(), checkfirst=True)
