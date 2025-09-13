import os
import threading
from datetime import datetime

# Custom imports
from .Globals import (
    file_manager, queue_manager
)
from .Vars import (
    logger, config,
    TEMP_DIR, DATA_DIR,
    get_episode_file_path, iter_episodes, log_manager, probe_streams, select_dubs, format_duration
)
from .MediaServerManager import scan_media_server



class MainLoop:
    def __init__(self, mdnx_api, notifier, config=config) -> None:
        self.mdnx_api = mdnx_api
        self.notifier = notifier
        self.config = config
        self.loop_timeout = int(self.config["app"]["CHECK_FOR_UPDATES_INTERVAL"])
        self.between_episode_timeout = int(self.config["app"]["BETWEEN_EPISODE_DL_WAIT_INTERVAL"])
        self.mainloop_iter = 0
        self.notifications_buffer = []

        logger.debug(f"[MainLoop] MainLoop initialized.")

        # Event to signal the loop to stop
        self.stop_event = threading.Event()

        # Thread that will run the loop
        self.thread = threading.Thread(target=self.mainloop, name="MainLoop")

    def start(self) -> None:
        logger.info("[MainLoop] Starting MainLoop...")
        self.thread.start()
        return

    def stop(self) -> None:
        logger.info("[MainLoop] Stopping MainLoop...")
        self.stop_event.set()
        if threading.current_thread() is not self.thread:  # avoid joining self
            self.thread.join()
        logger.info("[MainLoop] MainLoop stopped.")
        return

    def wait_or_interrupt(self, timeout: int) -> bool:
        if self.stop_event.wait(timeout=timeout):
            logger.info("[MainLoop] Stop event set. Exiting MainLoop...")
            return True
        return False

    def snapshot_episode(self, series_name, episode_info, file_path, action_label: str, before_dubs=None, before_subs=None) -> dict:
        try:
            after_dubs, after_subs = probe_streams(file_path, self.config["app"]["CHECK_MISSING_DUB_SUB_TIMEOUT"])
            derived = set(after_subs)
            for loc in list(after_subs):
                if "-" in loc:
                    derived.add(loc.split("-")[0])
            after_subs = derived
        except Exception:
            after_dubs = set()
            after_subs = set()

        if before_dubs is None:
            before_dubs = set()
        if before_subs is None:
            before_subs = set()

        return {
            "action": action_label,
            "series_name": series_name,
            "episode_name": episode_info.get("episode_name", ""),
            "episode_number": episode_info.get("episode_number", ""),
            "before_dubs": sorted(before_dubs),
            "before_subs": sorted(before_subs),
            "after_dubs": sorted(after_dubs),
            "after_subs": sorted(after_subs),
            "path": file_path,
        }

    def flush_notifications(self) -> None:
        if not self.notifications_buffer or self.notifier is None:
            self.notifications_buffer.clear()
            return

        new_items = []
        for notification in self.notifications_buffer:
            if notification["action"] == "new":
                new_items.append(notification)

        upd_items = []
        for notification in self.notifications_buffer:
            if notification["action"] == "updated":
                upd_items.append(notification)

        parts = []
        if new_items:
            parts.append(f"{len(new_items)} new")
        if upd_items:
            parts.append(f"{len(upd_items)} updated")

        when = datetime.now().strftime("%I:%M %p %d/%m/%Y")
        if parts:
            subject = f"Download summary: {', '.join(parts)} ({when})"
        else:
            subject = f"Download summary ({when})"

        lines = []
        if new_items:
            lines.append("New downloads:")
            lines.append("---------------------------")
            for item in new_items:
                lines += [
                    f"Series name: {item['series_name']}",
                    f"Episode name: {item['episode_name']}",
                    f"Episode number: {item['episode_number']}",
                    f"Episode dubs: {', '.join(item['after_dubs']) or 'None'}",
                    f"Episode subs: {', '.join(item['after_subs']) or 'None'}",
                    f"Episode path: {item['path']}",
                    ""
                ]
            lines.append("---------------------------")
            lines.append("")

        if upd_items:
            lines.append("Updates (new dub/sub detected):")
            lines.append("---------------------------")
            for item in upd_items:
                lines += [
                    f"Series name: {item['series_name']}",
                    f"Episode name: {item['episode_name']}",
                    f"Episode number: {item['episode_number']}",
                    f"Episode before dubs: {', '.join(item['before_dubs']) or 'None'}",
                    f"Episode before subs: {', '.join(item['before_subs']) or 'None'}",
                    f"Episode after dubs: {', '.join(item['after_dubs']) or 'None'}",
                    f"Episode after subs: {', '.join(item['after_subs']) or 'None'}",
                    f"Episode path: {item['path']}",
                    ""
                ]
            lines.append("---------------------------")

        body = "\n".join(lines).strip()

        try:
            self.notifier.notify(subject, body)
        finally:
            self.notifications_buffer.clear()

    def refresh_queue(self) -> bool:
        logger.info("[MainLoop] Getting the current queue IDs...")
        queue_output = queue_manager.output()
        if queue_output is not None:
            queue_ids = set(queue_output.keys())
        else:
            queue_ids = set()

        monitor_ids = set(config["monitor-series-id"])
        if not monitor_ids and not queue_ids:
            logger.info("[MainLoop] No series to monitor or stop monitoring.\nPlease add series IDs to 'monitor-series-id' in the config file to start monitoring.\nExiting...")
            return False

        # Start or update monitors
        logger.info("[MainLoop] Checking to see if any series need to be monitored...")
        for series_id in monitor_ids:
            if series_id not in queue_ids:
                logger.info(f"[MainLoop] Starting to monitor series with ID: {series_id}")
                self.mdnx_api.start_monitor(series_id)
            else:
                logger.info(f"[MainLoop] Series with ID: {series_id} is already being monitored. Updating with new data...")
                self.mdnx_api.update_monitor(series_id)

        # Stop monitors for IDs no longer in config
        logger.info("[MainLoop] Checking to see if any series need to be stopped from monitoring...")
        for series_id in queue_ids:
            if series_id not in monitor_ids:
                logger.info(f"[MainLoop] Stopping monitor for series with ID: {series_id}")
                self.mdnx_api.stop_monitor(series_id)

        logger.info("[MainLoop] MDNX queue refresh complete.")

        return True

    def mainloop(self) -> None:
        try:
            while not self.stop_event.is_set():
                logger.debug("[MainLoop] Executing main loop task.")
                refresh_ok = self.refresh_queue()
                if not refresh_ok:
                    self.stop()
                    return

                current_queue = queue_manager.output()

                if self.config["app"]["ONLY_CREATE_QUEUE"] == True:
                    logger.info("[MainLoop] ONLY_CREATE_QUEUE is True. Exiting after queue creation.\nIf docker-compose.yaml has 'restart: always/unless-stopped', please change it to 'restart: no' to prevent restart loop.")
                    self.stop()
                    return

                # download any missing / not yet downloaded episodes
                logger.info("[MainLoop] Checking for episodes to download.")
                for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(current_queue):

                    # Should episode be downloaded?
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
                            queue_manager.update_episode_status(series_id, season_key, episode_key, True)
                            continue
                        else:
                            logger.info(f"[MainLoop] Episode not found at {file_path} and 'episode_downloaded' status is False. Initiating download.")

                            dub_override = select_dubs(episode_info)

                            download_successful = self.mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number_download"], dub_override)
                            if download_successful:
                                logger.info(f"[MainLoop] Episode downloaded successfully.")

                                temp_path = os.path.join(TEMP_DIR, "output.mkv")

                                if file_manager.transfer(temp_path, file_path):
                                    logger.info("[MainLoop] Transfer complete.")
                                    queue_manager.update_episode_status(series_id, season_key, episode_key, True)
                                    series_name = current_queue[series_id]["series"]["series_name"]
                                    snapshot = self.snapshot_episode(series_name, episode_info, file_path, action_label="new")
                                    self.notifications_buffer.append(snapshot)
                                else:
                                    logger.error("[MainLoop] Transfer failed.")
                                    queue_manager.update_episode_status(series_id, season_key, episode_key, False)
                            else:
                                logger.error(f"[MainLoop] Episode download failed for {series_id} season {season_key} - {episode_key}.")
                                queue_manager.update_episode_status(series_id, season_key, episode_key, False)

                            file_manager.remove_temp_files()
                            logger.info(f"[MainLoop] Waiting for {format_duration(self.between_episode_timeout)} before next iteration.")
                            if self.wait_or_interrupt(timeout=self.between_episode_timeout):
                                return


                # Check for missing dubs and subs in downloaded files
                if self.config["app"]["CHECK_MISSING_DUB_SUB"] == True:
                    wanted_dubs = set()
                    for lang in self.config["mdnx"]["cli-defaults"]["dubLang"]:
                        wanted_dubs.add(lang.lower())

                    wanted_subs = set()
                    for lang in self.config["mdnx"]["cli-defaults"]["dlsubs"]:
                        wanted_subs.add(lang.lower())

                    logger.info("[MainLoop] Verifying language tracks in downloaded files.")
                    for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(current_queue):

                        file_path = get_episode_file_path(current_queue, series_id, season_key, episode_key, DATA_DIR)
                        episode_basename = os.path.basename(file_path)
                        if not os.path.exists(file_path):
                            continue

                        local_dubs, local_subs = probe_streams(file_path, self.config["app"]["CHECK_MISSING_DUB_SUB_TIMEOUT"])

                        derived = set(local_subs)
                        for loc in list(local_subs):
                            if "-" in loc:
                                derived.add(loc.split("-")[0]) # turn things like "en-in" to "en"
                        local_subs = derived

                        missing_dubs = wanted_dubs - local_dubs
                        missing_subs = wanted_subs - local_subs

                        if not missing_dubs and not missing_subs:
                            logger.info(f"[MainLoop] {episode_basename} has all required dubs and subs. No action needed.")
                            continue

                        avail_dubs = set()
                        for dub in episode_info.get("available_dubs", []):
                            avail_dubs.add(dub.lower())

                        avail_subs = set()
                        for sub in episode_info.get("available_subs", []):
                            avail_subs.add(sub.lower())

                        # only consider missing tracks that CR can actually provide
                        effective_missing_dubs = set()
                        for dub in missing_dubs:
                            if dub in avail_dubs:
                                effective_missing_dubs.add(dub)

                        effective_missing_subs = set()
                        for sub in missing_subs:
                            if sub in avail_subs:
                                effective_missing_subs.add(sub)

                        skip_download = False
                        if not effective_missing_dubs and not effective_missing_subs:
                            skip_download = True

                        logger.debug(
                            f"[MainLoop] {episode_basename}\ndubs: "
                            f"wanted={','.join(wanted_dubs) or 'None'} "
                            f"present={','.join(local_dubs) or 'None'} "
                            f"available={','.join(avail_dubs) or 'None'} "
                            f"downloading={','.join(effective_missing_dubs) or 'None'}\n"
                            f"subs: wanted={','.join(wanted_subs) or 'None'} "
                            f"present={','.join(local_subs) or 'None'} "
                            f"available={','.join(avail_subs) or 'None'} "
                            f"downloading={','.join(effective_missing_subs) or 'None'}\n"
                        )

                        if skip_download:
                            logger.info(f"[MainLoop] Skipping download for {episode_basename} as all required dubs and subs are present.")
                            continue

                        if effective_missing_dubs:
                            logger.info(f"[MainLoop] Missing dubs detected for {episode_basename}: {', '.join(effective_missing_dubs)}. Re-downloading episode to acquire missing dubs.")

                        if effective_missing_subs:
                            logger.info(f"[MainLoop] Missing dubs detected for {episode_basename}: {', '.join(effective_missing_subs)}. Re-downloading episode to acquire missing dubs.")

                        dub_override = select_dubs(episode_info)

                        if self.mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number_download"], dub_override):
                            temp_path = os.path.join(TEMP_DIR, self.config["mdnx"]["cli-defaults"]["fileName"] + ".mkv")
                            if file_manager.transfer(temp_path, file_path, overwrite=True):
                                logger.info("[MainLoop] Transfer complete.")
                                series_name = current_queue[series_id]["series"]["series_name"]
                                snapshot = self.snapshot_episode(series_name, episode_info, file_path, action_label="updated", before_dubs=local_dubs, before_subs=local_subs)
                                self.notifications_buffer.append(snapshot)
                            else:
                                logger.info("[MainLoop] Transfer failed")
                        else:
                            logger.error("[MainLoop] Re-download failed. Keeping existing file.")

                        file_manager.remove_temp_files()
                        logger.info(f"[MainLoop] Waiting for {format_duration(self.between_episode_timeout)} before next iteration.")
                        if self.wait_or_interrupt(timeout=self.between_episode_timeout):
                            return
                else:
                    logger.info("[MainLoop] CHECK_MISSING_DUB_SUB is False. Skipping dub/sub verification.")

                # house-keeping and loop control
                self.mainloop_iter += 1
                logger.info(f"[MainLoop] Current MainLoop iteration: {self.mainloop_iter}")

                # Perform housekeeping tasks every 10 iterations.
                if self.mainloop_iter == 10:
                    logger.info("[MainLoop] Truncating log file.")
                    log_manager()
                    logger.info("[MainLoop] Truncated log file.")
                    self.mainloop_iter = 0

                # Trigger media server scan if configured and there are new items in the notifications buffer.
                if len(self.notifications_buffer) > 0 and self.config["app"]["MEDIASERVER_TYPE"] is not None:
                    logger.info("[MainLoop] Triggering media server scan.")
                    scan_media_server()

                # Flush notifications buffer if it has items.
                if self.notifications_buffer:
                    logger.info("[MainLoop] Flushing notifications buffer.")
                    self.flush_notifications()

                # Wait for self.timeout seconds or exit early if stop_event is set.
                logger.info(f"[MainLoop] MainLoop iteration completed. Next iteration in {format_duration(self.loop_timeout)}.")
                if self.wait_or_interrupt(timeout=self.loop_timeout):
                    return
        finally:
            logger.info("[MainLoop] MainLoop exited.")
