"""sprint 6: PR module, Reddit distribution, Postiz-scheduled posts

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


journalist_lead_status_enum = postgresql.ENUM(
    "new", "pitched", "replied", "declined", name="journalist_lead_status_enum"
)
embargo_status_enum = postgresql.ENUM("pending", "lifted", "broken", name="embargo_status_enum")
reddit_post_status_enum = postgresql.ENUM(
    "draft", "scheduled", "posted", "removed", name="reddit_post_status_enum"
)
scheduled_post_status_enum = postgresql.ENUM(
    "draft", "scheduled", "published", "failed", name="scheduled_post_status_enum"
)


def upgrade() -> None:
    bind = op.get_bind()
    journalist_lead_status_enum.create(bind, checkfirst=True)
    embargo_status_enum.create(bind, checkfirst=True)
    reddit_post_status_enum.create(bind, checkfirst=True)
    scheduled_post_status_enum.create(bind, checkfirst=True)

    # --- PR module ---
    op.create_table(
        "press_kits",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False, unique=True, index=True,
        ),
        sa.Column("press_release", sa.Text(), nullable=False),
        sa.Column("synopsis", postgresql.JSONB(), nullable=False),
        sa.Column("bios", postgresql.JSONB(), nullable=False),
        sa.Column("quotes", postgresql.JSONB(), nullable=False),
        sa.Column("faq", postgresql.JSONB(), nullable=False),
        sa.Column("contact_info", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "journalist_leads",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("outlet", sa.String(length=255), nullable=True),
        sa.Column("beat", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", journalist_lead_status_enum, nullable=False, server_default="new"),
        sa.Column("pitch_text", sa.Text(), nullable=True),
        sa.Column("pitched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "embargoes",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column(
            "journalist_lead_id", sa.Integer(),
            sa.ForeignKey("journalist_leads.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("embargo_date", sa.Date(), nullable=False),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("status", embargo_status_enum, nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "coverage",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("outlet_name", sa.String(length=255), nullable=False),
        sa.Column("article_url", sa.String(length=1000), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("published_date", sa.Date(), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    # --- Reddit distribution ---
    op.create_table(
        "reddit_posts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("subreddit", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("flair", sa.String(length=100), nullable=True),
        sa.Column("disclosure_note", sa.String(length=255), nullable=False),
        sa.Column("status", reddit_post_status_enum, nullable=False, server_default="draft"),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("postiz_post_id", sa.String(length=255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("upvotes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "reddit_comments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "reddit_post_id", sa.Integer(), sa.ForeignKey("reddit_posts.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("comment_body", sa.Text(), nullable=False),
        sa.Column("suggested_reply", sa.Text(), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "reddit_karma",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("total_karma", sa.Integer(), nullable=False),
        sa.Column("post_karma", sa.Integer(), nullable=False),
        sa.Column("comment_karma", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="manual"),
    )

    # --- Postiz-scheduled posts ---
    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False, index=True,
        ),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("postiz_integration_id", sa.String(length=255), nullable=True),
        sa.Column("postiz_post_id", sa.String(length=255), nullable=True),
        sa.Column("status", scheduled_post_status_enum, nullable=False, server_default="draft"),
        sa.Column("scheduled_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("engagement_metrics", postgresql.JSONB(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("scheduled_posts")
    op.drop_table("reddit_karma")
    op.drop_table("reddit_comments")
    op.drop_table("reddit_posts")
    op.drop_table("coverage")
    op.drop_table("embargoes")
    op.drop_table("journalist_leads")
    op.drop_table("press_kits")

    bind = op.get_bind()
    scheduled_post_status_enum.drop(bind, checkfirst=True)
    reddit_post_status_enum.drop(bind, checkfirst=True)
    embargo_status_enum.drop(bind, checkfirst=True)
    journalist_lead_status_enum.drop(bind, checkfirst=True)
