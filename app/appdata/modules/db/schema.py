from sqlalchemy import Column, ForeignKeyConstraint, Integer, MetaData, Table, Text


metadata = MetaData()


queue_series = Table(
    "queue_series",
    metadata,
    Column("service", Text, primary_key=True, nullable=False),
    Column("series_id", Text, primary_key=True, nullable=False),
    Column("series_name", Text, nullable=False),
    Column("seasons_count", Text, nullable=True),
    Column("eps_count", Text, nullable=True),
    sqlite_with_rowid=False,
)


queue_seasons = Table(
    "queue_seasons",
    metadata,
    Column("service", Text, primary_key=True, nullable=False),
    Column("series_id", Text, primary_key=True, nullable=False),
    Column("season_key", Text, primary_key=True, nullable=False),
    Column("season_id", Text, nullable=False),
    Column("season_number", Text, nullable=False),
    Column("season_name", Text, nullable=False),
    ForeignKeyConstraint(
        ["service", "series_id"],
        ["queue_series.service", "queue_series.series_id"],
        ondelete="CASCADE",
    ),
    sqlite_with_rowid=False,
)


queue_episodes = Table(
    "queue_episodes",
    metadata,
    Column("service", Text, primary_key=True, nullable=False),
    Column("series_id", Text, primary_key=True, nullable=False),
    Column("season_key", Text, primary_key=True, nullable=False),
    Column("episode_key", Text, primary_key=True, nullable=False),
    Column("episode_id", Text, nullable=True),
    Column("episode_number", Text, nullable=False),
    Column("episode_number_download", Text, nullable=True),
    Column("episode_name", Text, nullable=False),
    Column("available_dubs", Text, nullable=False),
    Column("available_subs", Text, nullable=False),
    Column("available_qualities", Text, nullable=False),
    Column("episode_downloaded", Integer, nullable=False, server_default="0"),
    Column("episode_skip", Integer, nullable=False, server_default="0"),
    Column("has_all_dubs_subs", Integer, nullable=False, server_default="0"),
    ForeignKeyConstraint(
        ["service", "series_id", "season_key"],
        [
            "queue_seasons.service",
            "queue_seasons.series_id",
            "queue_seasons.season_key"
        ],
        ondelete="CASCADE",
    ),
    sqlite_with_rowid=False,
)
