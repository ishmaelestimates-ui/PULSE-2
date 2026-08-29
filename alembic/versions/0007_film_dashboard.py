"""sprint 7: film features (acts, trailer cuts, festivals, territories), dashboard (milestones, budget)

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-25

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


festival_match_status_enum = postgresql.ENUM(
    "suggested", "pending", "submitted", "accepted", "rejected", name="festival_match_status_enum"
)
territory_release_status_enum = postgresql.ENUM("planned", "released", name="territory_release_status_enum")
milestone_status_enum = postgresql.ENUM("pending", "in_progress", "done", name="milestone_status_enum")


def upgrade() -> None:
    bind = op.get_bind()
    festival_match_status_enum.create(bind, checkfirst=True)
    territory_release_status_enum.create(bind, checkfirst=True)
    milestone_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "film_acts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("act_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
    )

    op.create_table(
        "trailer_cuts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("clip_order", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Float(), nullable=False),
        sa.Column("end_time", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("scene_type", sa.String(length=50), nullable=False, server_default="Dialogue"),
        sa.Column("review_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "festival_matches",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("festival_name", sa.String(length=255), nullable=False),
        sa.Column("tier", sa.Integer(), nullable=False),
        sa.Column("why_relevant", sa.Text(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("entry_fee", sa.String(length=100), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", festival_match_status_enum, nullable=False, server_default="suggested"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "territory_releases",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("territory", sa.String(length=100), nullable=False),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("status", territory_release_status_enum, nullable=False, server_default="planned"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    op.create_table(
        "project_milestones",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("status", milestone_status_enum, nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "budget_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("spent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("budget_items")
    op.drop_table("project_milestones")
    op.drop_table("territory_releases")
    op.drop_table("festival_matches")
    op.drop_table("trailer_cuts")
    op.drop_table("film_acts")

    bind = op.get_bind()
    milestone_status_enum.drop(bind, checkfirst=True)
    territory_release_status_enum.drop(bind, checkfirst=True)
    festival_match_status_enum.drop(bind, checkfirst=True)
