"""add episodes.transcript_segments for frontend transcript sync

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "episodes", sa.Column("transcript_segments", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("episodes", "transcript_segments")
