import os
import json

from .Globals import log_manager
from .Vars import QUEUE_PATH, SERVICES


class QueueManager:
    def __init__(self, queue_path: str = QUEUE_PATH) -> None:
        self.queue_path = queue_path
        self.queue_data = self._load_queue()

        log_manager.debug(f"QueueManager initialized (path: {self.queue_path})")

    def add(self, new_data: dict, service: str) -> None:
        """Add or update series in the queue for the specified service."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        log_manager.debug(f"Adding series to the queue under '{bucket_name}'.")
        bucket = self.queue_data.setdefault(bucket_name, {})

        for series_id, series_info in new_data.items():
            # brand new series
            if series_id not in bucket:
                bucket[series_id] = series_info

                # ensure episode flags exist for downstream logic
                for season_info in series_info.get("seasons", {}).values():
                    for episode_info in season_info.get("episodes", {}).values():
                        episode_info.setdefault("episode_downloaded", False)
                        episode_info.setdefault("episode_skip", False)
                        episode_info.setdefault("has_all_dubs_subs", False)

                log_manager.debug(f"Added series '{series_id}' to '{bucket_name}'.")
                continue

            # if series already exists, update its info (except seasons/episodes)
            bucket[series_id]["series"] = series_info["series"]

            # normalize season keys to the real season_id when available,
            # and collapse any duplicates already present in the existing queue.
            existing_seasons = bucket[series_id].setdefault("seasons", {})

            # collapse duplicates already in the bucket (same season_id under different keys)
            seen = {}
            for old_key, old_season in list(existing_seasons.items()):
                season_id = old_season.get("season_id")

                if not season_id:
                    continue

                if season_id in seen:
                    keep_key = seen[season_id]
                    keep = existing_seasons[keep_key]

                    for episode_key, episode_value in old_season.get("episodes", {}).items():
                        if episode_key not in keep.setdefault("episodes", {}):
                            keep["episodes"][episode_key] = episode_value

                    del existing_seasons[old_key]
                else:
                    seen[season_id] = old_key

            # while ingesting new data, migrate target key to the stable season_id
            for season_key, season_info in series_info.get("seasons", {}).items():
                canonical_key = season_info.get("season_id") or season_key

                # if we already have this season under another key, move it
                if season_info.get("season_id"):
                    prev_key = seen.get(season_info["season_id"])
                    if prev_key and prev_key != canonical_key and prev_key in existing_seasons:

                        # if destination key exists, merge. otherwise re-key
                        if canonical_key in existing_seasons:
                            dst = existing_seasons[canonical_key]
                            src = existing_seasons[prev_key]

                            for episode_key, episode_value in src.get("episodes", {}).items():
                                if episode_key not in dst.setdefault("episodes", {}):
                                    dst["episodes"][episode_key] = episode_value

                            del existing_seasons[prev_key]
                        else:
                            existing_seasons[canonical_key] = existing_seasons.pop(prev_key)

                        seen[season_info["season_id"]] = canonical_key

                season = existing_seasons.setdefault(
                    canonical_key,
                    {**season_info, "episodes": {}}
                )

                for field_name, field_value in season_info.items():
                    if field_name == "episodes":
                        continue

                    season[field_name] = field_value

                for episode_key, new_episode in season_info.get("episodes", {}).items():
                    old_episode = season["episodes"].get(episode_key)

                    # if episode already exists, preserve its flags. otherwise initialize them.
                    if old_episode:
                        new_episode["episode_downloaded"] = old_episode.get("episode_downloaded", False)
                        new_episode["has_all_dubs_subs"] = old_episode.get("has_all_dubs_subs", False)
                        new_episode.setdefault("episode_skip", old_episode.get("episode_skip", False))
                    else:
                        new_episode.setdefault("episode_downloaded", False)
                        new_episode.setdefault("episode_skip", False)
                        new_episode.setdefault("has_all_dubs_subs", False)

                    season["episodes"][episode_key] = new_episode

            log_manager.debug(f"Updated series '{series_id}' in '{bucket_name}'.")

        self._save_queue()

    def remove(self, series_id: str, service: str) -> None:
        """Remove a series from the queue for the specified service."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        log_manager.debug(f"Removing series {series_id} from '{bucket_name}'.")
        bucket = self.queue_data.setdefault(bucket_name, {})

        if series_id in bucket:
            del bucket[series_id]
            self._save_queue()
            log_manager.debug(f"Removed series '{series_id}' from '{bucket_name}'.")
            return

        log_manager.warning(f"Series '{series_id}' not found in '{bucket_name}'.")

    def update_episode_status(self, series_id: str, season_id: str, episode_id: str, status: bool, service: str) -> None:
        """Update the 'episode_downloaded' flag for an episode."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        bucket = self.queue_data.setdefault(bucket_name, {})

        if series_id not in bucket:
            log_manager.warning(f"Series '{series_id}' not found in '{bucket_name}'.")
            return

        if season_id not in bucket[series_id]["seasons"]:
            log_manager.warning(f"Season '{season_id}' not found in series '{series_id}' ({bucket_name}).")
            return

        episodes = bucket[series_id]["seasons"][season_id].get("episodes", {})
        if episode_id not in episodes:
            log_manager.warning(
                f"Episode '{episode_id}' not found in season '{season_id}' for series '{series_id}' ({bucket_name})."
            )
            return

        episodes[episode_id]["episode_downloaded"] = status
        self._save_queue()
        log_manager.info(
            f"Updated episode '{episode_id}' in series '{series_id}', season '{season_id}' "
            f"to downloaded={status} ({bucket_name})."
        )

    def update_episode_has_all_dubs_subs(self, series_id: str, season_id: str, episode_id: str, status: bool, service: str) -> None:
        """Update the 'has_all_dubs_subs' flag for an episode."""

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return

        bucket = self.queue_data.setdefault(bucket_name, {})

        if series_id not in bucket:
            log_manager.warning(f"Series '{series_id}' not found in '{bucket_name}'.")
            return

        if season_id not in bucket[series_id]["seasons"]:
            log_manager.warning(f"Season '{season_id}' not found in series '{series_id}' ({bucket_name}).")
            return

        episodes = bucket[series_id]["seasons"][season_id].get("episodes", {})
        if episode_id not in episodes:
            log_manager.warning(
                f"Episode '{episode_id}' not found in season '{season_id}' for series '{series_id}' ({bucket_name})."
            )
            return

        episodes[episode_id]["has_all_dubs_subs"] = status
        self._save_queue()
        log_manager.info(
            f"Updated episode '{episode_id}' in series '{series_id}', season '{season_id}' "
            f"to has_all_dubs_subs={status} ({bucket_name})."
        )

    def output(self, service: str | None = None) -> dict | None:
        """Return the queue data, optionally scoped to a single service."""

        if not self.queue_data:
            return None

        if service is None:
            return self.queue_data

        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return None

        return self.queue_data.get(bucket_name, {})

    def _normalize_service(self, service: str) -> str | None:
        """Normalize service name to standard bucket names."""

        normalized_service = service.strip().lower()

        service_obj = SERVICES.get(normalized_service)
        if service_obj is None:
            log_manager.error(f"Unknown service '{service}'.")
            return None

        return service_obj.queue_bucket

    def _ensure_roots(self, data: dict) -> dict:
        """Ensure all queue roots exist in the queue data."""

        if not isinstance(data, dict):
            return self._empty_buckets()

        for service in SERVICES.all():
            data.setdefault(service.queue_bucket, {})
        return data

    def _empty_buckets(self) -> dict:
        """Return an empty queue dict with one bucket per service."""

        buckets = {}
        for service in SERVICES.all():
            buckets[service.queue_bucket] = {}
        return buckets

    def _load_queue(self) -> dict:
        """Load the queue from disk, or initialize a new one if not present or malformed."""

        if os.path.exists(self.queue_path):
            try:
                log_manager.debug(f"Loading queue from {self.queue_path}.")

                with open(self.queue_path, "r", encoding="utf-8") as data_file:
                    loaded = json.load(data_file)

                loaded = self._ensure_roots(loaded)
                log_manager.debug(f"Queue loaded from {self.queue_path}.")
                return loaded

            except json.JSONDecodeError:
                log_manager.error("Malformed JSON in queue file. Starting with an empty queue.")

            except Exception as e:
                log_manager.error(f"Error loading queue. Starting with an empty queue.\n{e}")

        else:
            log_manager.debug(f"Queue file not found at {self.queue_path}. Starting with an empty queue.")

        # create a new empty queue file on disk
        init = self._empty_buckets()

        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(init, f, indent=4, ensure_ascii=False)

        return init

    def _save_queue(self) -> None:
        """Save the current queue data to disk."""

        log_manager.debug("Saving queue.")

        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue_data, f, indent=4, ensure_ascii=False)

        log_manager.debug(f"Queue saved to {self.queue_path}.")
