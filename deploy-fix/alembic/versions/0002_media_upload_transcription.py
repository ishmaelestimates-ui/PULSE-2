"""media upload + transcription: media_files table, episodes.transcript nullable

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-23

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from app.db_compat import pg_enum, create_enum_if_pg, drop_enum_if_pg, JSONB_COMPAT

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


media_type_enum = pg_enum("audio", "video", name="media_type_enum")
transcription_status_enum = pg_enum(
    "none", "pending", "complete", "failed", name="transcription_status_enum"
)


def upgrade() -> None:
    bind = op.get_bind()
    create_enum_if_pg(media_type_enum, bind)
    create_enum_if_pg(transcription_status_enum, bind)

    # Episodes can now be created "media-first" (upload + transcribe
    # later), so a transcript is no longer required at creation time.
    op.alter_column("episodes", "transcript", existing_type=sa.Text(), nullable=True)

    # Use the already-created PostgreSQL ENUM directly.  The
    # enum_compat()/with_variant() wrapper can cause SQLAlchemy to issue a
    # second CREATE TYPE during op.create_table().  SQLite gets String for
    # local/dev compatibility.
    media_type_column = (
        media_type_enum if bind.dialect.name == "postgresql" else sa.String(length=50)
    )
    transcription_status_column = (
        transcription_status_enum
        if bind.dialect.name == "postgresql"
        else sa.String(length=50)
    )

    op.create_table(
        "media_files",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "episode_id",
            sa.Integer(),
            sa.ForeignKey("episodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("file_path", sa.String(length=1000), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column("media_type", media_type_column, nullable=False),
        sa.Column("audio_path", sa.String(length=1000), nullable=True),
        sa.Column("thumbnail_path", sa.String(length=1000), nullable=True),
        sa.Column(
            "transcription_status",
            transcription_status_column,
            nullable=False,
            server_default="none",
        ),
        sa.Column("media_metadata", JSONB_COMPAT, nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("media_files")
    op.alter_column("episodes", "transcript", existing_type=sa.Text(), nullable=False)
    drop_enum_if_pg(transcription_status_enum, op.get_bind())
    drop_enum_if_pg(media_type_enum, op.get_bind())
