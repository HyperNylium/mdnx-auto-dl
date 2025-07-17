import os
import time
import threading

# Custom imports
from .FileHandler import FileHandler
from .Vars import logger, config
from .Vars import TEMP_DIR, DATA_DIR
from .Vars import get_episode_file_path, iter_episodes, log_manager, refresh_queue, probe_streams

# Only for syntax highlighting in VSCode - remove in prod
# from .MDNX_API import MDNX_API



class MainLoop:
    # def __init__(self, mdnx_api: MDNX_API, config=config) -> None:
    def __init__(self, mdnx_api, config=config) -> None:
        self.mdnx_api = mdnx_api
        self.config = config
        self.timeout = int(config["app"]["CHECK_FOR_UPDATES_INTERVAL"])
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


            # download any missing / not yet downloaded episodes
            logger.info("[MainLoop] Checking for episodes to download.")
            for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(current_queue):

                # Skip special episode keys (for example, if the episode key starts with "S")
                if episode_key.startswith("S") and config["app"]["DOWNLOAD_SPECIAL_EPISODES"] == False:
                    logger.info(f"[MainLoop] Skipping special episode {episode_key} because DOWNLOAD_SPECIAL_EPISODES is False.")
                    continue

                # Skip PV episodes
                if episode_info["episode_name"].lower().startswith("pv"):
                    logger.info(f"[MainLoop] Skipping PV episode {episode_key}")
                    continue

                # Should episode be downloaded logic
                if episode_info["episode_downloaded"]:
                    logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_downloaded' status is True. Skipping download.")
                    continue
                else:
                    logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_downloaded' status is False. Checking file path to make sure file actually does not exist...")

                    # Construct the expected file path using the dynamic template.
                    file_path = get_episode_file_path(current_queue, series_id, season_key, episode_key, DATA_DIR)
                    logger.info(f"[MainLoop] Checking for episode at {file_path}.")

                    if os.path.exists(file_path):
                        logger.info(f"[MainLoop] Episode already exists at {file_path}. Updating 'episode_downloaded' status to True and skipping download.")
                        self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, True)
                        continue
                    else:
                        logger.info(f"[MainLoop] Episode not found at {file_path} and 'episode_downloaded' status is False. Initiating download.")
                        download_successful = self.mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number_download"])
                        if download_successful:
                            logger.info(f"[MainLoop] Episode downloaded successfully.")

                            temp_path = os.path.join(TEMP_DIR, config["mdnx"]["cli-defaults"]["fileName"])

                            if self.file_handler.transfer(temp_path, file_path):
                                logger.info("[MainLoop] Transfer complete.")
                                self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, True)
                            else:
                                logger.error("[MainLoop] Transfer failed.")
                                self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, False)

                        else:
                            logger.error(f"[MainLoop] Episode download failed for {series_id} season {season_key} - {episode_key}.")
                            self.mdnx_api.queue_manager.update_episode_status(series_id, season_key, episode_key, False)

                        self.file_handler.remove_temp_files()
                        logger.info(f"[MainLoop] Waiting for {config['app']['BETWEEN_EPISODE_DL_WAIT_INTERVAL']} seconds before next iteration.")
                        time.sleep(config["app"]["BETWEEN_EPISODE_DL_WAIT_INTERVAL"])  # sleep to avoid API rate limits


            # Check for missing dubs and subs in downloaded files
            if config["app"]["CHECK_MISSING_DUB_SUB"] == True:
                wanted_dubs = set()
                for lang in config["mdnx"]["cli-defaults"]["dubLang"]:
                    wanted_dubs.add(lang.lower())

                wanted_subs = set()
                for lang in config["mdnx"]["cli-defaults"]["dlsubs"]:
                    wanted_subs.add(lang.lower())

                logger.info("[MainLoop] Verifying language tracks in downloaded files.")
                for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(current_queue):

                    file_path = get_episode_file_path(current_queue, series_id, season_key, episode_key, DATA_DIR)
                    if not os.path.exists(file_path):
                        continue

                    local_dubs, local_subs = probe_streams(file_path, config["app"]["CHECK_MISSING_DUB_SUB_TIMEOUT"])

                    derived = set(local_subs)
                    for loc in list(local_subs):
                        if "-" in loc:
                            derived.add(loc.split("-")[0]) # turn things like "en-in" to "en"
                    local_subs = derived

                    missing_dubs = wanted_dubs - local_dubs
                    missing_subs = wanted_subs - local_subs

                    if not missing_dubs and not missing_subs:
                        logger.info(f"[MainLoop] {os.path.basename(file_path)} has all required dubs and subs. No action needed.")
                        continue

                    # If we reach here, we have missing dubs or subs
                    logger.info(f"[MainLoop] {os.path.basename(file_path)} has missing dubs or subs. Missing dubs: {', '.join(missing_dubs) if missing_dubs else 'None'}. Missing subs: {', '.join(missing_subs)if missing_subs else 'None'}.")

                    if self.mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number_download"]):
                        temp_path = os.path.join(TEMP_DIR, config["mdnx"]["cli-defaults"]["fileName"])
                        if self.file_handler.transfer(temp_path, file_path, overwrite=True):
                            logger.info("[MainLoop] Transfer complete.")
                        else:
                            logger.info("[MainLoop] Transfer failed")
                    else:
                        logger.error("[MainLoop] Re-download failed. Keeping existing file.")

                    self.file_handler.remove_temp_files()
                    logger.info(f"[MainLoop] Waiting for {config['app']['BETWEEN_EPISODE_DL_WAIT_INTERVAL']} seconds before next iteration.")
                    time.sleep(config["app"]["BETWEEN_EPISODE_DL_WAIT_INTERVAL"])
            else:
                logger.info("[MainLoop] CHECK_MISSING_DUB_SUB is False. Skipping dub/sub verification.")

            # house-keeping and loop control
            self.mainloop_iter += 1
            logger.info(f"[MainLoop] Current main loop iteration: {self.mainloop_iter}")

            # Perform housekeeping tasks every 10 iterations.
            if self.mainloop_iter == 10:
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