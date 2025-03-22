import os
import json

# Custom imports
from .Vars import logger, QUEUE_PATH



class QueueManager:
    def __init__(self, queue_path=QUEUE_PATH):
        self.queue_path = queue_path
        self.queue_data = self.load_queue()

    def load_queue(self) -> dict:
        if os.path.exists(self.queue_path):
            try:
                logger.info(f"[QueueManager] Loading queue from {self.queue_path}.")
                with open(self.queue_path, "r", encoding="utf-8") as data:
                    queue_data = json.load(data)
                    logger.info(f"[QueueManager] Queue loaded from {self.queue_path}.")
                    return queue_data
            except json.JSONDecodeError:
                logger.error("[QueueManager] Malformed JSON in queue file. Starting with an empty queue.")
            except Exception as e:
                logger.error(f"[QueueManager] Error loading queue. Starting with an empty queue.\n{e}")
        else:
            logger.info(f"[QueueManager] Queue file not found at {self.queue_path}. Starting with an empty queue.")

        # Create an empty queue file if it doesn't exist
        with open(self.queue_path, "a", encoding="utf-8") as empty_queue_file:
            empty_queue_file.write("{}")

        return {}

    def save_queue(self) -> None:
        logger.info("[QueueManager] Saving queue.")
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue_data, f, indent=4, ensure_ascii=False)
        logger.info(f"[QueueManager] Queue saved to {self.queue_path}.")

    def add(self, new_data: dict):
        logger.info("[QueueManager] Adding series to the queue.")
        for series_id, series_info in new_data.items():
            if series_id in self.queue_data:
                # Update existing entry with new data
                self.queue_data[series_id]["series"] = series_info["series"]
                self.queue_data[series_id]["seasons"].update(series_info["seasons"])
                self.queue_data[series_id]["episodes"].update(series_info["episodes"])
                logger.info(f"[QueueManager] Updated series '{series_id}' in the queue.")
            else:
                # Add a new entry to the queue
                self.queue_data[series_id] = series_info
                logger.info(f"[QueueManager] Added series '{series_id}' to the queue.")
        self.save_queue()

    def remove(self, series_id: str) -> None:
        logger.info(f"[QueueManager] Removing series {series_id} from the queue.")
        if series_id in self.queue_data:
            del self.queue_data[series_id]
            self.save_queue()
            logger.info(f"[QueueManager] Removed series '{series_id}' from the queue.")
        else:
            logger.warning(f"[QueueManager] Series '{series_id}' not found in the queue.")

    def update_episode_status(self, series_id: str, episode_id: str, status: bool) -> None:
        if series_id not in self.queue_data:
            logger.warning(f"[QueueManager] Series '{series_id}' not found in the queue.")
            return

        episodes = self.queue_data[series_id].get("episodes", {})
        if episode_id not in episodes:
            logger.warning(f"[QueueManager] Episode '{episode_id}' not found in series '{series_id}'.")
            return

        episodes[episode_id]["episode_downloaded"] = status
        self.save_queue()
        logger.info(f"[QueueManager] Updated episode '{episode_id}' in series '{series_id}' to downloaded={status}.")

    def output(self) -> dict | None:
        return self.queue_data if self.queue_data else None