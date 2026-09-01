"""sprint 8: user management (users, invites, magic links, activity), fame module

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-26

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.db_compat import pg_enum, enum_compat, create_enum_if_pg, drop_enum_if_pg, JSONB_COMPAT

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = pg_enum("admin", "editor", name="user_role_enum")
invite_role_enum = pg_enum("admin", "editor", name="invite_role_enum")
invite_status_enum = pg_enum("pending", "accepted", "expired", "revoked", name="invite_status_enum")
mention_sentiment_enum = pg_enum(
    "positive", "negative", "neutral", "unanalyzed", name="mention_sentiment_enum"
)
cultural_footprint_type_enum = pg_enum(
    "meme", "reference", "citation", "other", name="cultural_footprint_type_enum"
)


def upgrade() -> None:
    bind = op.get_bind()
    create_enum_if_pg(user_role_enum, bind)
    create_enum_if_pg(invite_role_enum, bind)
    create_enum_if_pg(invite_status_enum, bind)
    create_enum_if_pg(mention_sentiment_enum, bind)
    create_enum_if_pg(cultural_footprint_type_enum, bind)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", enum_compat(user_role_enum), nullable=False, server_default="editor"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "invites",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("email", sa.String(length=255), nullable=False, index=True),
        sa.Column("role", enum_compat(invite_role_enum), nullable=False, server_default="editor"),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("status", enum_compat(invite_status_enum), nullable=False, server_default="pending"),
        sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token", sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "activity_log_entries",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "fame_score_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("components", JSONB_COMPAT, nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "mentions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("sentiment", enum_compat(mention_sentiment_enum), nullable=False, server_default="unanalyzed"),
        sa.Column("found_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "competitor_benchmarks",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("competitor_name", sa.String(length=255), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("competitor_value", sa.Float(), nullable=False),
        sa.Column("our_value", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "cultural_footprint_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id", sa.Integer(), sa.ForeignKey("episodes.id", ondelete="CASCADE"), nullable=False, index=True
        ),
        sa.Column("item_type", enum_compat(cultural_footprint_type_enum), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("cultural_footprint_items")
    op.drop_table("competitor_benchmarks")
    op.drop_table("mentions")
    op.drop_table("fame_score_snapshots")
    op.drop_table("activity_log_entries")
    op.drop_table("magic_link_tokens")
    op.drop_table("invites")
    op.drop_table("users")

    bind = op.get_bind()
    drop_enum_if_pg(cultural_footprint_type_enum, bind)
    drop_enum_if_pg(mention_sentiment_enum, bind)
    drop_enum_if_pg(invite_status_enum, bind)
    drop_enum_if_pg(invite_role_enum, bind)
    drop_enum_if_pg(user_role_enum, bind)
