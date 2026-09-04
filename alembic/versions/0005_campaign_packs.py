"""campaign pack: campaign_packs table

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.db_compat import JSONB_COMPAT

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
        sa.Column("social_posts", JSONB_COMPAT, nullable=False),
        sa.Column("hooks", JSONB_COMPAT, nullable=False),
        sa.Column("schedule", JSONB_COMPAT, nullable=False),
        sa.Column("press_blurb", sa.Text(), nullable=False),
        sa.Column("newsletter", JSONB_COMPAT, nullable=False),
        sa.Column("show_notes", sa.Text(), nullable=False),
        sa.Column("trailer_cutlist", JSONB_COMPAT, nullable=False),
        sa.Column("hype_scores", JSONB_COMPAT, nullable=False),
        sa.Column("viral_predictions", JSONB_COMPAT, nullable=False),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("campaign_packs")
