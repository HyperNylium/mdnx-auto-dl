import os
import time
import threading

# Custom imports
from .FileHandler import FileHandler
from .Vars import logger, config
from .Vars import get_episode_file_path, iter_episodes, log_manager, refresh_queue

# Only for syntax highlighting in VSCode - remove in prod
# from .MDNX_API import MDNX_API



class MainLoop:
    # def __init__(self, mdnx_api: MDNX_API, config=config) -> None:
    def __init__(self, mdnx_api, config=config) -> None:
        self.mdnx_api = mdnx_api
        self.config = config
        self.timeout = int(config["app"]["MAIN_LOOP_UPDATE_INTERVAL"])
        self.mainloop_iter = 0

        logger.info(f"[MainLoop] MainLoop initialized.")

        # Initialize FileHandler
        self.file_handler = FileHandler()

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
            refresh_queue(self.mdnx_api)
            current_queue = self.mdnx_api.queue_manager.output()

            logger.info("[MainLoop] Checking for episodes to download.")
            for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(current_queue):

                # Optionally skip non-standard (special) episode keys (e.g., if key starts with "S")
                if episode_key.startswith("S") and config["app"]["MAIN_LOOP_DOWNLOAD_SPECIAL_EPISODES"] == False:
                    logger.info(f"[MainLoop] Skipping special episode {episode_key} because MAIN_LOOP_DOWNLOAD_SPECIAL_EPISODES is False.")
                    continue

                # Should episode be downloaded logic
                if episode_info["episode_downloaded"]:
                    logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_downloaded' status is True. Skipping download.")
                    continue
                else:
                    logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_downloaded' status is False. Checking file path to make sure file actually does not exist...")

                    # Construct the expected file path using the dynamic template.
                    file_path = get_episode_file_path(current_queue, series_id, season_key, episode_key, config["app"]["DATA_DIR"])
                    logger.info(f"[MainLoop] Checking for episode at {file_path}.")

                    if os.path.exists(file_path):
                        logger.info(f"[MainLoop] Episode already exists at {file_path}. Updating 'episode_downloaded' status to True and skipping download.")
                        self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, True)
                        continue
                    else:
                        logger.info(f"[MainLoop] Episode not found at {file_path} and 'episode_downloaded' status is False. Initiating download.")
                        download_successful = self.mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number"])
                        if download_successful:
                            logger.info(f"[MainLoop] Episode downloaded successfully.")

                            temp_path = os.path.join(config["app"]["TEMP_DIR"], "output.mkv")

                            if self.file_handler.transfer(temp_path, file_path):
                                logger.info(f"[MainLoop] Transfer complete.")
                                self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, True)
                            else:
                                logger.error(f"[MainLoop] Transfer failed.")
                                self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, False)

                        else:
                            logger.error(f"[MainLoop] Episode download failed for {series_id} season {season_key} - {episode_key}.")
                            self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, False)

                        self.file_handler.remove_temp_files()
                        logger.info(f"[MainLoop] Waiting for {config['app']['MAIN_LOOP_BETWEEN_EPISODE_WAIT_INTERVAL']} seconds before next iteration.")
                        time.sleep(config["app"]["MAIN_LOOP_BETWEEN_EPISODE_WAIT_INTERVAL"])  # sleep to avoid API rate limits

            self.mainloop_iter += 1
            logger.info(f"[MainLoop] Current main loop iteration: {self.mainloop_iter}")

            # Perform housekeeping tasks every 30 iterations.
            if self.mainloop_iter == 30:
                logger.info("[MainLoop] Truncating log file.")
                log_manager()
                logger.info("[MainLoop] Truncated log file.")
                self.mainloop_iter = 0

            logger.info(f"[MainLoop] Task executed at: {time.ctime()}")

            # Wait for self.timeout seconds or exit early if stop_event is set.
            if self.stop_event.wait(timeout=self.timeout):
                logger.info("[MainLoop] Main loop task interrupted.")
                break

        logger.info("[MainLoop] Main loop exited.")
        return