"""add isolated editor autosave snapshots

Revision ID: 0010_autosaves
Revises: 0009_reddit_intelligence
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_autosaves"
down_revision = "0009_reddit_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "autosaves",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_autosaves_episode_id", "autosaves", ["episode_id"])
    op.create_index("ix_autosaves_user_id", "autosaves", ["user_id"])
    op.create_index("ix_autosaves_saved_at", "autosaves", ["saved_at"])


def downgrade() -> None:
    op.drop_index("ix_autosaves_saved_at", table_name="autosaves")
    op.drop_index("ix_autosaves_user_id", table_name="autosaves")
    op.drop_index("ix_autosaves_episode_id", table_name="autosaves")
    op.drop_table("autosaves")
