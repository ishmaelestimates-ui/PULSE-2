"""coloring + brand settings: color_grades, brand_settings tables

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


color_grade_source_enum = postgresql.ENUM(
    "lut", "style_transfer", name="color_grade_source_enum"
)


def upgrade() -> None:
    bind = op.get_bind()
    color_grade_source_enum.create(bind, checkfirst=True)

    op.create_table(
        "color_grades",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source", color_grade_source_enum, nullable=False),
        sa.Column("lut_name", sa.String(length=100), nullable=True),
        sa.Column("style_transfer_params", postgresql.JSONB(), nullable=True),
        sa.Column("reference_image_path", sa.String(length=1000), nullable=True),
        sa.Column("preview_path", sa.String(length=1000), nullable=False),
        sa.Column("graded_media_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "brand_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "primary_color", sa.String(length=9), nullable=False, server_default="#6C5CE7"
        ),
        sa.Column(
            "secondary_color", sa.String(length=9), nullable=False, server_default="#00E676"
        ),
        sa.Column("tertiary_color", sa.String(length=9), nullable=True),
        sa.Column("font", sa.String(length=100), nullable=False, server_default="Inter"),
        sa.Column("logo_path", sa.String(length=1000), nullable=True),
        sa.Column("intro_music_path", sa.String(length=1000), nullable=True),
        sa.Column("outro_music_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("brand_settings")
    op.drop_table("color_grades")
    color_grade_source_enum.drop(op.get_bind(), checkfirst=True)
