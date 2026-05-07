"""initial schema

Revision ID: 94f62e2c18c0
Revises: 
Create Date: 2026-05-06 07:57:19.169683

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('queue_series',
        sa.Column('service', sa.Text(), nullable=False),
        sa.Column('series_id', sa.Text(), nullable=False),
        sa.Column('series_data', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('service', 'series_id'),
        sqlite_with_rowid=False
    )
    op.create_table('queue_seasons',
        sa.Column('service', sa.Text(), nullable=False),
        sa.Column('series_id', sa.Text(), nullable=False),
        sa.Column('season_key', sa.Text(), nullable=False),
        sa.Column('season_id', sa.Text(), nullable=False),
        sa.Column('season_number', sa.Text(), nullable=False),
        sa.Column('season_name', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['service', 'series_id'], ['queue_series.service', 'queue_series.series_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('service', 'series_id', 'season_key'),
        sqlite_with_rowid=False
    )
    op.create_table('queue_episodes',
        sa.Column('service', sa.Text(), nullable=False),
        sa.Column('series_id', sa.Text(), nullable=False),
        sa.Column('season_key', sa.Text(), nullable=False),
        sa.Column('episode_key', sa.Text(), nullable=False),
        sa.Column('episode_id', sa.Text(), nullable=True),
        sa.Column('episode_number', sa.Text(), nullable=False),
        sa.Column('episode_number_download', sa.Text(), nullable=True),
        sa.Column('episode_name', sa.Text(), nullable=False),
        sa.Column('available_dubs', sa.Text(), nullable=False),
        sa.Column('available_subs', sa.Text(), nullable=False),
        sa.Column('available_qualities', sa.Text(), nullable=False),
        sa.Column('episode_downloaded', sa.Integer(), server_default='0', nullable=False),
        sa.Column('episode_skip', sa.Integer(), server_default='0', nullable=False),
        sa.Column('has_all_dubs_subs', sa.Integer(), server_default='0', nullable=False),
        sa.ForeignKeyConstraint(['service', 'series_id', 'season_key'], ['queue_seasons.service', 'queue_seasons.series_id', 'queue_seasons.season_key'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('service', 'series_id', 'season_key', 'episode_key'),
        sqlite_with_rowid=False
    )


def downgrade() -> None:
    op.drop_table('queue_episodes')
    op.drop_table('queue_seasons')
    op.drop_table('queue_series')
