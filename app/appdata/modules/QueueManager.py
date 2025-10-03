import os
import json

# Custom imports
from .Vars import (
    logger,
    QUEUE_PATH
)


class QueueManager:
    def __init__(self, queue_path=QUEUE_PATH):
        self.queue_path = queue_path
        self.queue_data = self.load_queue()

    def _normalize_service(self, service: str) -> str | None:
        # This functions entire existence is because i am lazy and dont know what i'll put in as the name lol
        key = str(service or "").strip().lower()
        if key in {"cr", "crunchy", "crunchyroll"}:
            return "Crunchyroll"
        if key in {"hd", "hidive"}:
            return "HiDive"
        logger.error(f"[QueueManager] Unknown service '{service}'.")
        return None

    def _ensure_roots(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return {"Crunchyroll": {}, "HiDive": {}}

        # migrate legacy format
        if "Crunchyroll" not in data and "HiDive" not in data:
            logger.info("[QueueManager] Migrating legacy queue format to namespaced layout under 'Crunchyroll'.")
            data = {"Crunchyroll": data, "HiDive": {}}

        # ensure both roots exist
        data.setdefault("Crunchyroll", {})
        data.setdefault("HiDive", {})
        return data

    def load_queue(self) -> dict:
        if os.path.exists(self.queue_path):
            try:
                logger.debug(f"[QueueManager] Loading queue from {self.queue_path}.")
                with open(self.queue_path, "r", encoding="utf-8") as data_file:
                    loaded = json.load(data_file)
                loaded = self._ensure_roots(loaded)
                logger.debug(f"[QueueManager] Queue loaded from {self.queue_path}.")
                return loaded
            except json.JSONDecodeError:
                logger.error("[QueueManager] Malformed JSON in queue file. Starting with an empty queue.")
            except Exception as e:
                logger.error(f"[QueueManager] Error loading queue. Starting with an empty queue.\n{e}")
        else:
            logger.debug(f"[QueueManager] Queue file not found at {self.queue_path}. Starting with an empty queue.")

        init = {"Crunchyroll": {}, "HiDive": {}}
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(init, f, indent=4, ensure_ascii=False)
        return init

    def save_queue(self) -> None:
        logger.debug("[QueueManager] Saving queue.")
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue_data, f, indent=4, ensure_ascii=False)
        logger.debug(f"[QueueManager] Queue saved to {self.queue_path}.")

    def add(self, new_data: dict, service: str):
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return
        logger.debug(f"[QueueManager] Adding series to the queue under '{bucket_name}'.")
        bucket = self.queue_data.setdefault(bucket_name, {})

        for series_id, series_info in new_data.items():
            if series_id not in bucket:
                bucket[series_id] = series_info
                for s in series_info.get("seasons", {}).values():
                    for ep in s.get("episodes", {}).values():
                        ep.setdefault("episode_downloaded", False)
                logger.debug(f"[QueueManager] Added series '{series_id}' to '{bucket_name}'.")
                continue

            # series exists: merge
            bucket[series_id]["series"] = series_info["series"]

            for season_key, season_info in series_info.get("seasons", {}).items():
                season = bucket[series_id]["seasons"].setdefault(
                    season_key, {**season_info, "episodes": {}}
                )
                season.update({k: v for k, v in season_info.items() if k != "episodes"})

                for ep_key, new_ep in season_info.get("episodes", {}).items():
                    old_ep = season["episodes"].get(ep_key)
                    if old_ep:
                        new_ep["episode_downloaded"] = old_ep.get("episode_downloaded", False)
                    else:
                        new_ep.setdefault("episode_downloaded", False)

                    season["episodes"][ep_key] = new_ep

            logger.debug(f"[QueueManager] Updated series '{series_id}' in '{bucket_name}'.")
        self.save_queue()

    def remove(self, series_id: str, service: str) -> None:
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return
        logger.debug(f"[QueueManager] Removing series {series_id} from '{bucket_name}'.")
        bucket = self.queue_data.setdefault(bucket_name, {})
        if series_id in bucket:
            del bucket[series_id]
            self.save_queue()
            logger.debug(f"[QueueManager] Removed series '{series_id}' from '{bucket_name}'.")
        else:
            logger.warning(f"[QueueManager] Series '{series_id}' not found in '{bucket_name}'.")

    def update_episode_status(self, series_id: str, season_id: str, episode_id: str, status: bool, service: str) -> None:
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return
        bucket = self.queue_data.setdefault(bucket_name, {})

        if series_id not in bucket:
            logger.warning(f"[QueueManager] Series '{series_id}' not found in '{bucket_name}'.")
            return

        if season_id not in bucket[series_id]["seasons"]:
            logger.warning(f"[QueueManager] Season '{season_id}' not found in series '{series_id}' ({bucket_name}).")
            return

        episodes = bucket[series_id]["seasons"][season_id].get("episodes", {})
        if episode_id not in episodes:
            logger.warning(f"[QueueManager] Episode '{episode_id}' not found in season '{season_id}' for series '{series_id}' ({bucket_name}).")
            return

        episodes[episode_id]["episode_downloaded"] = status
        self.save_queue()
        logger.info(f"[QueueManager] Updated episode '{episode_id}' in series '{series_id}', season '{season_id}' to downloaded={status} ({bucket_name}).")

    def output(self, service: str | None = None) -> dict | None:
        if not self.queue_data:
            return None
        if service is None:
            return self.queue_data
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return None
        return self.queue_data.get(bucket_name, {})
