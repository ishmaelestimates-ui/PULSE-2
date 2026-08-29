"""campaign pack: campaign_packs table

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaign_packs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("social_posts", postgresql.JSONB(), nullable=False),
        sa.Column("hooks", postgresql.JSONB(), nullable=False),
        sa.Column("schedule", postgresql.JSONB(), nullable=False),
        sa.Column("press_blurb", sa.Text(), nullable=False),
        sa.Column("newsletter", postgresql.JSONB(), nullable=False),
        sa.Column("show_notes", sa.Text(), nullable=False),
        sa.Column("trailer_cutlist", postgresql.JSONB(), nullable=False),
        sa.Column("hype_scores", postgresql.JSONB(), nullable=False),
        sa.Column("viral_predictions", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("campaign_packs")
