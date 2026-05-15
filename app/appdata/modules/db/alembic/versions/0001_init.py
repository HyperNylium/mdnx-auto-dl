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
    op.create_table('series',
        sa.Column('service', sa.Text(), nullable=False),
        sa.Column('series_id', sa.Text(), nullable=False),
        sa.Column('series_name', sa.Text(), nullable=False),
        sa.Column('seasons_count', sa.Text(), nullable=True),
        sa.Column('eps_count', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('service', 'series_id'),
        sqlite_with_rowid=False
    )
    op.create_table('seasons',
        sa.Column('service', sa.Text(), nullable=False),
        sa.Column('series_id', sa.Text(), nullable=False),
        sa.Column('season_key', sa.Text(), nullable=False),
        sa.Column('season_id', sa.Text(), nullable=False),
        sa.Column('season_number', sa.Text(), nullable=False),
        sa.Column('season_name', sa.Text(), nullable=False),
        sa.Column('eps_count', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['service', 'series_id'], ['series.service', 'series.series_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('service', 'series_id', 'season_key'),
        sqlite_with_rowid=False
    )
    op.create_table('episodes',
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
        sa.ForeignKeyConstraint(['service', 'series_id', 'season_key'], ['seasons.service', 'seasons.series_id', 'seasons.season_key'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('service', 'series_id', 'season_key', 'episode_key'),
        sqlite_with_rowid=False
    )


def downgrade() -> None:
    op.drop_table('episodes')
    op.drop_table('seasons')
    op.drop_table('series')
