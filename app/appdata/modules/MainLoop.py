import os
import time
import threading

# Custom imports
from .Vars import logger, config
from .Vars import get_episode_file_path

# Only for syntax highlighting in VSCode - remove in prod
from .MDNX_API import MDNX_API



class MainLoop:
    def __init__(self, mdnx_api: MDNX_API, config=config) -> None:
        logger.info(f"[MainLoop] MainLoop initialized.")
        self.mdnx_api = mdnx_api
        self.config = config
        self.timeout = int(config["app"]["MAIN_LOOP_UPDATE_INTERVAL"])

        # Event to signal the loop to stop
        self.stop_event = threading.Event()

        # Thread that will run the loop
        self.thread = threading.Thread(target=self.mainloop, name="MainLoop")

    def start(self) -> None:
        logger.info("[MainLoop] Starting main loop.")
        self.thread.start()
        logger.info("[MainLoop] Main loop started.")
        return

    def stop(self) -> None:
        logger.info("[MainLoop] Stopping main loop.")
        self.stop_event.set()
        self.thread.join()
        logger.info("[MainLoop] Main loop stopped.")
        return

    def mainloop(self) -> None:
        while not self.stop_event.is_set():

            logger.info("[MainLoop] Executing main loop task.")
            base_dir = config["mdnx"]["dir-path"]["content"]
            current_queue = self.mdnx_api.queue_manager.output()

            logger.info("[MainLoop] Checking for episodes to download.")
            for series_id, series_data in current_queue.items():
                # Iterate over seasons and episodes to check if they need to be downloaded.
                for season_key in series_data["seasons"]:
                    for episode_key, episode_info in series_data["episodes"].items():
                        # Optionally skip non-standard episode keys (e.g., if key starts with "S") - this will be optional in the future.
                        if not episode_key.startswith("E"):
                            continue

                        if not episode_info["episode_downloaded"]:
                            logger.info(f"[MainLoop] Episode {episode_key} for series {series_id} needs to be downloaded.")

                            # Construct the expected file path using the dynamic template.
                            file_path = get_episode_file_path(current_queue, series_id, season_key, episode_key, base_dir)
                            logger.info(f"[MainLoop] Checking for episode at {file_path}.")

                            if os.path.exists(file_path):
                                logger.info(f"[MainLoop] Episode already exists at {file_path}. Skipping download.")
                                self.mdnx_api.queue_manager.update_episode_status(series_id, episode_key, True)
                            else:
                                logger.info(f"[MainLoop] Episode not found at {file_path}. Initiating download.")
                                download_successful = self.mdnx_api.download_episode(series_id, episode_key)
                                if download_successful:
                                    logger.info(f"[MainLoop] Episode downloaded successfully.")
                                    self.mdnx_api.queue_manager.update_episode_status(series_id, episode_key, True)
                                else:
                                    logger.error(f"[MainLoop] Episode download failed for {series_id} - {episode_key}.")
                                    self.mdnx_api.queue_manager.update_episode_status(series_id, episode_key, False)

            logger.info(f"[MainLoop] Task executed at: {time.ctime()}")

            # Wait for self.timeout amount of time or exit early if stop_event is set
            if self.stop_event.wait(timeout=self.timeout):
                break

        logger.info("[MainLoop] Main loop exited.")
        return