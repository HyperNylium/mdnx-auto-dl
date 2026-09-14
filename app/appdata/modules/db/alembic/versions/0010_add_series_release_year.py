"""add series release_year column

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("series", schema=None) as batch_op:
        batch_op.add_column(sa.Column("release_year", sa.Text(), nullable=False, server_default=""))


def downgrade() -> None:
    op.drop_column("series", "release_year")
