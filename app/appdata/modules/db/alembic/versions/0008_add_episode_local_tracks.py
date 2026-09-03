"""add episode local dubs and subs cache columns

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("episodes", schema=None, recreate="always") as batch_op:
        batch_op.add_column(sa.Column("local_dubs", sa.Text(), nullable=True), insert_after="available_audio_qualities")
        batch_op.add_column(sa.Column("local_subs", sa.Text(), nullable=True), insert_after="local_dubs")


def downgrade() -> None:
    with op.batch_alter_table("episodes", schema=None) as batch_op:
        batch_op.drop_column("local_subs")
        batch_op.drop_column("local_dubs")
