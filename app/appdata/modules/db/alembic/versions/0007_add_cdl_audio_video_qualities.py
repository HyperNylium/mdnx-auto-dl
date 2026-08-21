"""add cdl audio and video quality columns

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("episodes", schema=None) as batch_op:
        batch_op.alter_column("available_qualities", new_column_name="available_video_qualities")
        batch_op.add_column(sa.Column("available_audio_qualities", sa.Text(), nullable=False, server_default=sa.text("'{}'")))

    # the old available_qualities held a list, the new column holds a dict, so reset both to an empty dict.
    # the queue is regenerated data and refills on the next refresh anyways.
    op.execute("UPDATE episodes SET available_video_qualities = '{}'")
    op.execute("UPDATE episodes SET available_audio_qualities = '{}'")


def downgrade() -> None:
    with op.batch_alter_table("episodes", schema=None) as batch_op:
        batch_op.drop_column("available_audio_qualities")
        batch_op.alter_column("available_video_qualities", new_column_name="available_qualities")

    op.execute("UPDATE episodes SET available_qualities = '[]'")
