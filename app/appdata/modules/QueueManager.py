import os
import json

# Custom imports
from .Globals import log_manager
from .Vars import QUEUE_PATH


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
        log_manager.log(f"Unknown service '{service}'.", level="error")
        return None

    def _ensure_roots(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return {"Crunchyroll": {}, "HiDive": {}}

        # migrate legacy format
        if "Crunchyroll" not in data and "HiDive" not in data:
            log_manager.log("Migrating legacy queue format to namespaced layout under 'Crunchyroll'.")
            data = {"Crunchyroll": data, "HiDive": {}}

        # ensure both roots exist
        data.setdefault("Crunchyroll", {})
        data.setdefault("HiDive", {})
        return data

    def load_queue(self) -> dict:
        if os.path.exists(self.queue_path):
            try:
                log_manager.log(f"Loading queue from {self.queue_path}.", level="debug")
                with open(self.queue_path, "r", encoding="utf-8") as data_file:
                    loaded = json.load(data_file)
                loaded = self._ensure_roots(loaded)
                log_manager.log(f"Queue loaded from {self.queue_path}.", level="debug")
                return loaded
            except json.JSONDecodeError:
                log_manager.log("Malformed JSON in queue file. Starting with an empty queue.", level="error")
            except Exception as e:
                log_manager.log(f"Error loading queue. Starting with an empty queue.\n{e}", level="error")
        else:
            log_manager.log(f"Queue file not found at {self.queue_path}. Starting with an empty queue.", level="debug")

        init = {"Crunchyroll": {}, "HiDive": {}}
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(init, f, indent=4, ensure_ascii=False)
        return init

    def save_queue(self) -> None:
        log_manager.log("Saving queue.", level="debug")
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue_data, f, indent=4, ensure_ascii=False)
        log_manager.log(f"Queue saved to {self.queue_path}.", level="debug")

    def add(self, new_data: dict, service: str):
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return
        log_manager.log(f"Adding series to the queue under '{bucket_name}'.", level="debug")
        bucket = self.queue_data.setdefault(bucket_name, {})

        for series_id, series_info in new_data.items():
            if series_id not in bucket:
                bucket[series_id] = series_info
                for s in series_info.get("seasons", {}).values():
                    for ep in s.get("episodes", {}).values():
                        ep.setdefault("episode_downloaded", False)
                        ep.setdefault("episode_skip", False)
                log_manager.log(f"Added series '{series_id}' to '{bucket_name}'.", level="debug")
                continue

            # series exists: merge
            bucket[series_id]["series"] = series_info["series"]

            # canonicalize season keys to the real season_id when available,
            # and collapse any duplicates already present in the existing queue.
            existing_seasons = bucket[series_id].setdefault("seasons", {})

            # collapse duplicates already in the bucket (same season_id under different keys)
            seen = {}
            for old_key, old_season in list(existing_seasons.items()):
                sid = old_season.get("season_id")
                if not sid:
                    continue
                if sid in seen:
                    keep_key = seen[sid]
                    keep = existing_seasons[keep_key]
                    for ep_key, ep_val in old_season.get("episodes", {}).items():
                        if ep_key not in keep.setdefault("episodes", {}):
                            keep["episodes"][ep_key] = ep_val
                    del existing_seasons[old_key]
                else:
                    seen[sid] = old_key

            # while ingesting new data, migrate target key to the stable season_id
            for season_key, season_info in series_info.get("seasons", {}).items():
                canonical_key = season_info.get("season_id") or season_key

                # if we already have this season under another key, move it
                prev_key = None
                if season_info.get("season_id"):
                    prev_key = seen.get(season_info["season_id"])
                    if prev_key and prev_key != canonical_key and prev_key in existing_seasons:
                        # if destination key exists, merge. otherwise re-key
                        if canonical_key in existing_seasons:
                            dst = existing_seasons[canonical_key]
                            src = existing_seasons[prev_key]
                            for ep_key, ep_val in src.get("episodes", {}).items():
                                if ep_key not in dst.setdefault("episodes", {}):
                                    dst["episodes"][ep_key] = ep_val
                            del existing_seasons[prev_key]
                        else:
                            existing_seasons[canonical_key] = existing_seasons.pop(prev_key)
                        seen[season_info["season_id"]] = canonical_key

                season = existing_seasons.setdefault(
                    canonical_key, {**season_info, "episodes": {}}
                )
                season.update({k: v for k, v in season_info.items() if k != "episodes"})

                for ep_key, new_ep in season_info.get("episodes", {}).items():
                    old_ep = season["episodes"].get(ep_key)
                    if old_ep:
                        new_ep["episode_downloaded"] = old_ep.get("episode_downloaded", False)
                    else:
                        new_ep.setdefault("episode_downloaded", False)
                    new_ep["episode_skip"] = new_ep.get("episode_skip", False)
                    season["episodes"][ep_key] = new_ep

            log_manager.log(f"Updated series '{series_id}' in '{bucket_name}'.", level="debug")
        self.save_queue()

    def remove(self, series_id: str, service: str) -> None:
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return
        log_manager.log(f"Removing series {series_id} from '{bucket_name}'.", level="debug")
        bucket = self.queue_data.setdefault(bucket_name, {})
        if series_id in bucket:
            del bucket[series_id]
            self.save_queue()
            log_manager.log(f"Removed series '{series_id}' from '{bucket_name}'.", level="debug")
        else:
            log_manager.log(f"Series '{series_id}' not found in '{bucket_name}'.", level="warning")

    def update_episode_status(self, series_id: str, season_id: str, episode_id: str, status: bool, service: str) -> None:
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return
        bucket = self.queue_data.setdefault(bucket_name, {})

        if series_id not in bucket:
            log_manager.log(f"Series '{series_id}' not found in '{bucket_name}'.", level="warning")
            return

        if season_id not in bucket[series_id]["seasons"]:
            log_manager.log(f"Season '{season_id}' not found in series '{series_id}' ({bucket_name}).", level="warning")
            return

        episodes = bucket[series_id]["seasons"][season_id].get("episodes", {})
        if episode_id not in episodes:
            log_manager.log(f"Episode '{episode_id}' not found in season '{season_id}' for series '{series_id}' ({bucket_name}).", level="warning")
            return

        episodes[episode_id]["episode_downloaded"] = status
        self.save_queue()
        log_manager.log(f"Updated episode '{episode_id}' in series '{series_id}', season '{season_id}' to downloaded={status} ({bucket_name}).")

    def output(self, service: str | None = None) -> dict | None:
        if not self.queue_data:
            return None
        if service is None:
            return self.queue_data
        bucket_name = self._normalize_service(service)
        if bucket_name is None:
            return None
        return self.queue_data.get(bucket_name, {})
