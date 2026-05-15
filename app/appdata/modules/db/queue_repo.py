import json
import sqlite3
import threading

from appdata.modules.types.queue import Queue, ServiceBucket, Series, Season, Episode, SeriesInfo


_write_lock = threading.Lock()


_ALLOWED_EPISODE_FIELDS = {
    "episode_downloaded",
    "episode_skip",
    "has_all_dubs_subs"
}


def load_queue(conn: sqlite3.Connection) -> Queue:
    """Load the whole queue into memory as a nested Queue object."""

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM series ORDER BY service, series_id")
    series_rows = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM seasons "
        "ORDER BY service, series_id, "
        "CAST(SUBSTR(season_key, 2) AS INTEGER)"
    )
    season_rows = cursor.fetchall()

    cursor.execute(
        "SELECT * FROM episodes "
        "ORDER BY service, series_id, "
        "CAST(SUBSTR(season_key, 2) AS INTEGER), "
        "SUBSTR(episode_key, 1, 1), "
        "CAST(SUBSTR(episode_key, 2) AS INTEGER)"
    )
    episode_rows = cursor.fetchall()
    cursor.close()

    buckets: dict[str, ServiceBucket] = {}

    for series_row in series_rows:
        service = series_row["service"]
        series_id = series_row["series_id"]

        bucket = buckets.setdefault(service, ServiceBucket())
        bucket.series[series_id] = Series(
            series=SeriesInfo(
                series_name=series_row["series_name"],
                series_id=series_id,
                seasons_count=series_row["seasons_count"],
                eps_count=series_row["eps_count"]
            ),
            seasons={}
        )

    for season_row in season_rows:
        service = season_row["service"]
        series_id = season_row["series_id"]

        bucket = buckets.get(service)
        if bucket is None:
            continue

        series_obj = bucket.series.get(series_id)
        if series_obj is None:
            continue

        series_obj.seasons[season_row["season_key"]] = Season(
            season_id=season_row["season_id"],
            season_number=season_row["season_number"],
            season_name=season_row["season_name"],
            eps_count=season_row["eps_count"],
            episodes={}
        )

    for episode_row in episode_rows:
        service = episode_row["service"]
        series_id = episode_row["series_id"]
        season_key = episode_row["season_key"]

        bucket = buckets.get(service)
        if bucket is None:
            continue

        series_obj = bucket.series.get(series_id)
        if series_obj is None:
            continue

        season_obj = series_obj.seasons.get(season_key)
        if season_obj is None:
            continue

        season_obj.episodes[episode_row["episode_key"]] = Episode(
            episode_id=episode_row["episode_id"],
            episode_number=episode_row["episode_number"],
            episode_number_download=episode_row["episode_number_download"],
            episode_name=episode_row["episode_name"],
            available_dubs=json.loads(episode_row["available_dubs"]),
            available_subs=json.loads(episode_row["available_subs"]),
            available_qualities=json.loads(episode_row["available_qualities"]),
            episode_downloaded=bool(episode_row["episode_downloaded"]),
            episode_skip=bool(episode_row["episode_skip"]),
            has_all_dubs_subs=bool(episode_row["has_all_dubs_subs"])
        )

    return Queue(buckets=buckets)


def clear_queue(conn: sqlite3.Connection) -> None:
    """Delete all rows from all tables."""

    with _write_lock:
        with conn:
            conn.execute("DELETE FROM series")


def upsert_series(conn: sqlite3.Connection, service: str, series_id: str, series: Series) -> None:
    """Insert or replace one series row, and all its seasons/episodes."""

    series.series.seasons_count = str(len(series.seasons))

    total_episodes = 0
    for season in series.seasons.values():
        total_episodes += len(season.episodes)
    series.series.eps_count = str(total_episodes)

    for season in series.seasons.values():
        season.eps_count = str(len(season.episodes))

    with _write_lock:
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO series "
                "(service, series_id, series_name, seasons_count, eps_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    service,
                    series_id,
                    series.series.series_name,
                    series.series.seasons_count,
                    series.series.eps_count
                )
            )

            conn.execute(
                "DELETE FROM seasons WHERE service = ? AND series_id = ?",
                (service, series_id)
            )

            for season_key, season in series.seasons.items():
                conn.execute(
                    "INSERT INTO seasons "
                    "(service, series_id, season_key, season_id, season_number, season_name, eps_count) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        service,
                        series_id,
                        season_key,
                        season.season_id,
                        season.season_number,
                        season.season_name,
                        season.eps_count
                    )
                )

                for episode_key, episode in season.episodes.items():
                    conn.execute(
                        "INSERT INTO episodes "
                        "(service, series_id, season_key, episode_key, episode_id, "
                        "episode_number, episode_number_download, episode_name, "
                        "available_dubs, available_subs, available_qualities, "
                        "episode_downloaded, episode_skip, has_all_dubs_subs) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (
                            service,
                            series_id,
                            season_key,
                            episode_key,
                            episode.episode_id,
                            episode.episode_number,
                            episode.episode_number_download,
                            episode.episode_name,
                            json.dumps(episode.available_dubs),
                            json.dumps(episode.available_subs),
                            json.dumps(episode.available_qualities),
                            int(episode.episode_downloaded),
                            int(episode.episode_skip),
                            int(episode.has_all_dubs_subs)
                        )
                    )


def delete_series(conn: sqlite3.Connection, service: str, series_id: str) -> None:
    """Delete one series and all its seasons/episodes."""

    with _write_lock:
        with conn:
            conn.execute(
                "DELETE FROM series WHERE service = ? AND series_id = ?",
                (service, series_id)
            )


def set_episode_field(conn: sqlite3.Connection, service: str, series_id: str, season_key: str, episode_key: str, field: str, value: bool) -> None:
    """Set one of the boolean fields of an episode."""

    if field not in _ALLOWED_EPISODE_FIELDS:
        raise ValueError(f"Refusing to update unknown field: {field!r}")

    with _write_lock:
        with conn:
            conn.execute(
                f"UPDATE episodes SET {field} = ? WHERE service = ? AND series_id = ? AND season_key = ? AND episode_key = ?",
                (int(value), service, series_id, season_key, episode_key)
            )
