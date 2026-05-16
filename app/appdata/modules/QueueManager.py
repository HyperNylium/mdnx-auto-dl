import sys
import threading

from .Globals import log_manager
from .Vars import (
    config,
    SERVICES,
    update_app_config
)
from .db.connection import open_connection
from .db.queue_repo import (
    delete_series, load_queue, set_episode_field, clear_queue, upsert_series
)
from .types.queue import Queue, Season, Series, ServiceBucket


class QueueManager:
    def __init__(self) -> None:
        self.conn = open_connection()
        self.queue = load_queue(self.conn)
        self._ensure_buckets()
        self._lock = threading.Lock()

        log_manager.debug("QueueManager initialized")

        if config.app.clear_queue:
            log_manager.info("CLEAR_QUEUE is True. Clearing queue tables.")
            clear_queue(self.conn)
            self.queue = Queue()
            self._ensure_buckets()
            update_app_config("CLEAR_QUEUE", False)
            log_manager.info("CLEAR_QUEUE is True. Cleared the queue and flipped CLEAR_QUEUE back to False. Exiting to restart with a clean slate.")
            sys.exit(0)

    def add(self, new_data: dict[str, Series], service: str) -> None:
        """Add or update series in the queue for the specified service."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        log_manager.debug(f"Adding series to the queue under '{bucket_name}'.")

        with self._lock:
            bucket = self.queue.buckets.setdefault(bucket_name, ServiceBucket())

            for series_id, new_series in new_data.items():
                existing_series = bucket.series.get(series_id)

                if existing_series is None:
                    bucket.series[series_id] = new_series
                    log_manager.debug(f"Added series '{series_id}' to '{bucket_name}'.")
                    upsert_series(self.conn, bucket_name, series_id, new_series)
                    continue

                # update only the SeriesInfo blob, leave existing seasons alone for merge
                existing_series.series = new_series.series

                # collapse any existing duplicates in current seasons by season_id
                seen: dict[str, str] = {}
                for old_key, old_season in list(existing_series.seasons.items()):
                    if old_season.season_id == "":
                        continue
                    if old_season.season_id in seen:
                        keep_key = seen[old_season.season_id]
                        keep = existing_series.seasons[keep_key]
                        for episode_key, episode_value in old_season.episodes.items():
                            if episode_key not in keep.episodes:
                                keep.episodes[episode_key] = episode_value
                        del existing_series.seasons[old_key]
                    else:
                        seen[old_season.season_id] = old_key

                # merge incoming seasons. always key by the season_key (S1, S2, etc).
                # if the same season_id appears under a different old key, rename to the new key.
                for season_key, new_season in new_series.seasons.items():
                    if new_season.season_id:
                        prev_key = seen.get(new_season.season_id)
                        if prev_key and prev_key != season_key and prev_key in existing_series.seasons:
                            if season_key in existing_series.seasons:
                                dst = existing_series.seasons[season_key]
                                src = existing_series.seasons[prev_key]
                                for episode_key, episode_value in src.episodes.items():
                                    if episode_key not in dst.episodes:
                                        dst.episodes[episode_key] = episode_value
                                del existing_series.seasons[prev_key]
                            else:
                                existing_series.seasons[season_key] = existing_series.seasons.pop(prev_key)
                            seen[new_season.season_id] = season_key

                    existing_season = existing_series.seasons.get(season_key)
                    if existing_season is None:
                        existing_season = Season(
                            season_id=new_season.season_id,
                            season_number=new_season.season_number,
                            season_name=new_season.season_name,
                            episodes={}
                        )
                        existing_series.seasons[season_key] = existing_season
                    else:
                        existing_season.season_id = new_season.season_id
                        existing_season.season_number = new_season.season_number
                        existing_season.season_name = new_season.season_name

                    for episode_key, new_episode in new_season.episodes.items():
                        old_episode = existing_season.episodes.get(episode_key)
                        if old_episode is not None:
                            new_episode.episode_downloaded = old_episode.episode_downloaded
                            new_episode.has_all_dubs_subs = old_episode.has_all_dubs_subs
                        existing_season.episodes[episode_key] = new_episode

                    # drop episodes the service no longer lists for this season
                    stale_episode_keys = []
                    for existing_episode_key in existing_season.episodes:
                        if existing_episode_key not in new_season.episodes:
                            stale_episode_keys.append(existing_episode_key)
                    for stale_episode_key in stale_episode_keys:
                        del existing_season.episodes[stale_episode_key]

                # drop seasons the service no longer lists for this series
                stale_season_keys = []
                for existing_season_key in existing_series.seasons:
                    if existing_season_key not in new_series.seasons:
                        stale_season_keys.append(existing_season_key)
                for stale_season_key in stale_season_keys:
                    del existing_series.seasons[stale_season_key]

                upsert_series(self.conn, bucket_name, series_id, existing_series)
                log_manager.debug(f"Updated series '{series_id}' in '{bucket_name}'.")

    def remove(self, series_id: str, service: str) -> None:
        """Remove a series from the queue for the specified service."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        log_manager.debug(f"Removing series {series_id} from '{bucket_name}'.")

        with self._lock:
            bucket = self.queue.buckets.setdefault(bucket_name, ServiceBucket())

            if series_id in bucket.series:
                del bucket.series[series_id]
                delete_series(self.conn, bucket_name, series_id)
                log_manager.debug(f"Removed series '{series_id}' from '{bucket_name}'.")
                return

            log_manager.warning(f"Series '{series_id}' not found in '{bucket_name}'.")

    def update_episode_status(self, series_id: str, season_key: str, episode_key: str, status: bool, service: str) -> None:
        """Update the episode_downloaded flag for an episode."""

        self._set_flag(series_id, season_key, episode_key, "episode_downloaded", status, service)

    def update_episode_has_all_dubs_subs(self, series_id: str, season_key: str, episode_key: str, status: bool, service: str) -> None:
        """Update the has_all_dubs_subs flag for an episode."""

        self._set_flag(series_id, season_key, episode_key, "has_all_dubs_subs", status, service)

    def output(self, service: str | None = None) -> Queue | ServiceBucket | None:
        """Return the whole queue, the bucket for one service, or None if the service is unknown."""

        if service is None:
            return self.queue

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return None

        return self.queue.buckets.setdefault(bucket_name, ServiceBucket())

    def close(self) -> None:
        """Close the database connection."""

        try:
            self.conn.close()
            log_manager.info("Queue DB connection closed.")
        except Exception as e:
            log_manager.error(f"Error closing queue DB connection: {e}")

    def _set_flag(self, series_id: str, season_key: str, episode_key: str, field: str, status: bool, service: str) -> None:
        """Helper method to set a boolean flag on an episode and persist the change."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        with self._lock:
            bucket = self.queue.buckets.setdefault(bucket_name, ServiceBucket())

            series_obj = bucket.series.get(series_id)
            if series_obj is None:
                log_manager.warning(f"Series '{series_id}' not found in '{bucket_name}'.")
                return

            season_obj = series_obj.seasons.get(season_key)
            if season_obj is None:
                log_manager.warning(f"Season '{season_key}' not found in series '{series_id}' ({bucket_name}).")
                return

            episode_obj = season_obj.episodes.get(episode_key)
            if episode_obj is None:
                log_manager.warning(f"Episode '{episode_key}' not found in season '{season_key}' for series '{series_id}' ({bucket_name}).")
                return

            setattr(episode_obj, field, status)
            set_episode_field(self.conn, bucket_name, series_id, season_key, episode_key, field, status)

        log_manager.info(f"Updated episode '{episode_key}' in series '{series_id}', season '{season_key}' to {field}={status} ({bucket_name}).")

    def _normalize_service(self, service: str) -> str | None:
        """Normalize a service name to its standard queue bucket name."""

        normalized = service.strip().lower()
        service_obj = SERVICES.get(normalized)
        if service_obj is None:
            log_manager.error(f"Unknown service '{service}'.")
            return None
        return service_obj.queue_bucket

    def _ensure_buckets(self) -> None:
        """Make sure every registered service has an entry in self.queue.buckets."""

        for service in SERVICES.all():
            self.queue.buckets.setdefault(service.queue_bucket, ServiceBucket())
