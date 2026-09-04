"""add persistent Reddit community intelligence

Revision ID: 0009_reddit_intelligence
Revises: 0008_users_fame
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_reddit_intelligence"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reddit_community_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("fit_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("community_dna", sa.JSON(), nullable=False),
        sa.Column("rules_summary", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reddit_community_snapshots_episode_id", "reddit_community_snapshots", ["episode_id"])
    op.create_index("ix_reddit_community_snapshots_subreddit", "reddit_community_snapshots", ["subreddit"])

    op.create_table(
        "reddit_opportunities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("opportunity_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("suggested_contribution", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reddit_opportunities_episode_id", "reddit_opportunities", ["episode_id"])
    op.create_index("ix_reddit_opportunities_subreddit", "reddit_opportunities", ["subreddit"])


def downgrade() -> None:
    op.drop_index("ix_reddit_opportunities_subreddit", table_name="reddit_opportunities")
    op.drop_index("ix_reddit_opportunities_episode_id", table_name="reddit_opportunities")
    op.drop_table("reddit_opportunities")
    op.drop_index("ix_reddit_community_snapshots_subreddit", table_name="reddit_community_snapshots")
    op.drop_index("ix_reddit_community_snapshots_episode_id", table_name="reddit_community_snapshots")
    op.drop_table("reddit_community_snapshots")
