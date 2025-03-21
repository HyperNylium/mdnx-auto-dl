import os
import json

# Custom imports
from .Vars import logger, QUEUE_PATH



class QueueManager:
    def __init__(self, queue_path=QUEUE_PATH):
        self.queue_path = queue_path
        self.queue_data = self.load_queue()

    def load_queue(self):
        if os.path.exists(self.queue_path):
            try:
                with open(self.queue_path, "r", encoding="utf-8") as data:
                    return json.load(data)
            except json.JSONDecodeError:
                logger.error("Malformed JSON in queue file. Starting with an empty queue.")
                return {}
        else:
            os.makedirs(os.path.dirname(self.queue_path), exist_ok=True)
        return {}

    def save_queue(self):
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Queue saved to {self.queue_path}.")

    def add(self, new_data: dict):
        for series_id, series_info in new_data.items():
            if series_id in self.queue_data:
                # Update existing entry:
                self.queue_data[series_id]["series"] = series_info["series"]
                self.queue_data[series_id]["seasons"].update(series_info["seasons"])
                self.queue_data[series_id]["episodes"].update(series_info["episodes"])
                logger.info(f"Updated series '{series_id}' in the queue.")
            else:
                # Add a new entry:
                self.queue_data[series_id] = series_info
                logger.info(f"Added series '{series_id}' to the queue.")
        self.save_queue()

    def remove(self, series_id: str):
        if series_id in self.queue_data:
            del self.queue_data[series_id]
            self.save_queue()
            logger.info(f"Removed series '{series_id}' from the queue.")
        else:
            logger.warning(f"Series '{series_id}' not found in the queue.")

    def update_episode_status(self, series_id: str, episode_id: str, status: bool):
        if series_id not in self.queue_data:
            logger.warning(f"Series '{series_id}' not found in the queue.")
            return

        episodes = self.queue_data[series_id].get("episodes", {})
        if episode_id not in episodes:
            logger.warning(f"Episode '{episode_id}' not found in series '{series_id}'.")
            return

        episodes[episode_id]["episode_downloaded"] = status
        self.save_queue()
        logger.info(f"Updated episode '{episode_id}' in series '{series_id}' to downloaded={status}.")

    def output(self):
        return self.queue_data if self.queue_data else None