import os
import threading
from datetime import datetime
from rapidfuzz import process, fuzz

# Custom imports
from .MediaServerManager import mediaserver_scan_library
from .Globals import (
    file_manager, queue_manager
)
from .Vars import (
    logger, config,
    TEMP_DIR, DATA_DIR,
    get_episode_file_path, log_manager, probe_streams, select_dubs, format_duration, iter_episodes
)


class MainLoop:
    def __init__(self, cr_mdnx_api, hidive_mdnx_api, notifier) -> None:
        self.cr_mdnx_api = cr_mdnx_api
        self.hidive_mdnx_api = hidive_mdnx_api
        self.cr_enabled = config["app"]["CR_ENABLED"]
        self.hidive_enabled = config["app"]["HIDIVE_ENABLED"]
        self.check_missing_dub_sub = config["app"]["CHECK_MISSING_DUB_SUB"]
        self.notifier = notifier
        self.loop_timeout = int(config["app"]["CHECK_FOR_UPDATES_INTERVAL"])
        self.between_episode_timeout = int(config["app"]["BETWEEN_EPISODE_DL_WAIT_INTERVAL"])
        self.mainloop_iter = 0
        self.notifications_buffer = []
        self.fuzzy_matching_enabled = config["app"]["FUZZY_MATCHING_ENABLED"]
        self.fuzzy_threshold = config["app"]["FUZZY_MATCHING_THRESHOLD"]

        logger.debug("[MainLoop] MainLoop initialized.")

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
            after_dubs, after_subs = probe_streams(file_path, config["app"]["CHECK_MISSING_DUB_SUB_TIMEOUT"])
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

        cr_monitor_ids = set(config["cr_monitor_series_id"].keys())
        hd_monitor_ids = set(config["hidive_monitor_series_id"].keys())

        def process_service(service, enabled, api, monitor_ids):
            if not enabled or api is None:
                logger.info(f"[MainLoop] {service} is disabled or API not initialized. Skipping monitor refresh.")
                return True

            # Only look at the correct bucket inside queue.json
            bucket = queue_manager.output(service) or {}
            queue_ids = set(bucket.keys())

            if not monitor_ids and not queue_ids:
                logger.info(f"[MainLoop] No {service} series to monitor/stop. (both monitor list and queue are empty)")
                return True

            # Start or update monitors
            logger.info(f"[MainLoop] Checking {service} monitors...")
            for series_id in monitor_ids:
                if series_id not in queue_ids:
                    logger.info(f"[MainLoop] [{service}] Starting monitor for {series_id}")
                    api.start_monitor(series_id)
                else:
                    logger.info(f"[MainLoop] [{service}] Updating monitor for {series_id}")
                    api.update_monitor(series_id)

            # Stop monitors for series removed from config
            logger.info(f"[MainLoop] Checking {service} monitors to stop...")
            for series_id in queue_ids:
                if series_id not in monitor_ids:
                    logger.info(f"[MainLoop] [{service}] Stopping monitor for {series_id}")
                    api.stop_monitor(series_id)

            logger.info(f"[MainLoop] {service} monitor refresh complete.")
            return True

        ok_cr = process_service(
            service="Crunchyroll",
            enabled=self.cr_enabled,
            api=self.cr_mdnx_api,
            monitor_ids=cr_monitor_ids,
        )

        ok_hd = process_service(
            service="HiDive",
            enabled=self.hidive_enabled,
            api=self.hidive_mdnx_api,
            monitor_ids=hd_monitor_ids,
        )

        logger.info("[MainLoop] MDNX queue refresh complete.")
        return ok_cr and ok_hd

    def download_for_service(self, service, mdnx_api, current_queue):
        logger.info(f"[MainLoop] Checking for episodes to download from {service}...")

        bucket = current_queue.get(service, {})

        for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(bucket):

            if episode_info["episode_skip"]:
                logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_skip' is True. Skipping download.")
                continue

            if episode_info["episode_downloaded"]:
                logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_downloaded' status is True. Skipping download.")
                continue

            logger.info(f"[MainLoop] Episode {episode_info['episode_number']} ({episode_info['episode_name']}) 'episode_downloaded' status is False. Checking file path to make sure file actually does not exist...")

            # Construct the expected file path using the dynamic template.
            file_path = get_episode_file_path(bucket, series_id, season_key, episode_key, DATA_DIR)
            logger.info(f"[MainLoop] Checking for episode at {file_path}.")

            if os.path.exists(file_path):
                logger.info(f"[MainLoop] Episode already exists at {file_path}. Updating 'episode_downloaded' status to True and skipping download.")
                queue_manager.update_episode_status(series_id, season_key, episode_key, True, service)
                continue
            else:
                if self.fuzzy_matching_enabled:
                    expected_series_dirname = os.path.basename(os.path.dirname(os.path.dirname(file_path)))
                    expected_season_dirname = os.path.basename(os.path.dirname(file_path))
                    expected_episode_filename = os.path.basename(file_path)
                    logger.debug(f"[MainLoop] Fuzzy on: series='{expected_series_dirname}', season='{expected_season_dirname}', episode='{expected_episode_filename}', threshold={self.fuzzy_threshold}.")

                    # get series directories under DATA_DIR
                    series_directory_names = []
                    try:
                        data_dir_entries = os.listdir(DATA_DIR)
                    except Exception as list_error:
                        logger.error(f"[MainLoop] Could not list DATA_DIR '{DATA_DIR}': {list_error}")
                        data_dir_entries = []
                    logger.debug(f"[MainLoop] DATA_DIR entries: {len(data_dir_entries)}")

                    for entry_name in data_dir_entries:
                        candidate_series_path = os.path.join(DATA_DIR, entry_name)
                        if os.path.isdir(candidate_series_path):
                            series_directory_names.append(entry_name)
                    logger.debug(f"[MainLoop] Series dirs found: {len(series_directory_names)}")

                    found_episode_full_path = None

                    # fuzzy match the series directory
                    series_match = None
                    if series_directory_names:
                        series_match = process.extractOne(expected_series_dirname, series_directory_names, scorer=fuzz.WRatio)
                    logger.debug(f"[MainLoop] Series match: {series_match}")

                    if not series_match or series_match[1] < self.fuzzy_threshold:
                        logger.debug(f"[MainLoop] Series match below threshold or none. Skipping.")
                    else:
                        real_series_directory = os.path.join(DATA_DIR, series_match[0])
                        logger.debug(f"[MainLoop] Series accepted: '{series_match[0]}' (score {series_match[1]}) -> {real_series_directory}")

                        # get season directories under the matched series
                        season_directory_names = []
                        try:
                            series_dir_entries = os.listdir(real_series_directory)
                        except Exception as list_error:
                            logger.error(f"[MainLoop] Could not list series dir '{real_series_directory}': {list_error}")
                            series_dir_entries = []

                        for entry_name in series_dir_entries:
                            candidate_season_path = os.path.join(real_series_directory, entry_name)
                            if os.path.isdir(candidate_season_path):
                                season_directory_names.append(entry_name)

                        # fuzzy match the season directory
                        season_match = None
                        if season_directory_names:
                            season_match = process.extractOne(expected_season_dirname, season_directory_names, scorer=fuzz.WRatio)
                        logger.debug(f"[MainLoop] Season match: {season_match}")

                        if not season_match or season_match[1] < self.fuzzy_threshold:
                            logger.debug(f"[MainLoop] Season match below threshold or none. Skipping.")
                        else:
                            real_season_directory = os.path.join(real_series_directory, season_match[0])
                            logger.debug(f"[MainLoop] Season accepted: '{season_match[0]}' (score {season_match[1]}) -> {real_season_directory}")

                            # gather MKV files under the matched season
                            episode_filenames = []
                            try:
                                season_dir_entries = os.listdir(real_season_directory)
                            except Exception as list_error:
                                logger.error(f"[MainLoop] Could not list season dir '{real_season_directory}': {list_error}")
                                season_dir_entries = []

                            for entry_name in season_dir_entries:
                                candidate_episode_path = os.path.join(real_season_directory, entry_name)
                                if os.path.isfile(candidate_episode_path) and entry_name.lower().endswith(".mkv"):
                                    episode_filenames.append(entry_name)

                            # fuzzy match the episode filename
                            episode_match = None
                            if episode_filenames:
                                episode_match = process.extractOne(expected_episode_filename, episode_filenames, scorer=fuzz.WRatio)
                            logger.debug(f"[MainLoop] Episode match: {episode_match}")

                            if not episode_match or episode_match[1] < self.fuzzy_threshold:
                                logger.debug(f"[MainLoop] Episode match below threshold or none. Skipping.")
                            else:
                                found_episode_full_path = os.path.join(real_season_directory, episode_match[0])
                                logger.debug(f"[MainLoop] Episode accepted: '{episode_match[0]}' (score {episode_match[1]}) -> {found_episode_full_path}")

                    # if we found a fuzzy match, treat as present
                    if found_episode_full_path is not None and os.path.exists(found_episode_full_path):
                        logger.info(f"[MainLoop] Episode found via fuzzy match at {found_episode_full_path}. Treating as present.")
                        queue_manager.update_episode_status(series_id, season_key, episode_key, True, service)
                        continue

                logger.info(f"[MainLoop] Episode not found at {file_path} and 'episode_downloaded' status is False. Initiating download.")

                dub_override = select_dubs(episode_info)

                download_successful = mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number_download"], dub_override)
                if download_successful:
                    logger.info("[MainLoop] Episode downloaded successfully.")

                    temp_path = os.path.join(TEMP_DIR, "output.mkv")

                    if file_manager.transfer(temp_path, file_path):
                        logger.info("[MainLoop] Transfer complete.")
                        queue_manager.update_episode_status(series_id, season_key, episode_key, True, service)
                        series_name = bucket[series_id]["series"]["series_name"]
                        snapshot = self.snapshot_episode(series_name, episode_info, file_path, action_label="new")
                        self.notifications_buffer.append(snapshot)
                    else:
                        logger.error("[MainLoop] Transfer failed.")
                        queue_manager.update_episode_status(series_id, season_key, episode_key, False, service)
                else:
                    logger.error(f"[MainLoop] Episode download failed for {series_id} season {season_key} - {episode_key}.")
                    queue_manager.update_episode_status(series_id, season_key, episode_key, False, service)

                file_manager.remove_temp_files()
                logger.info(f"[MainLoop] Waiting for {format_duration(self.between_episode_timeout)} before next iteration.")
                if self.wait_or_interrupt(timeout=self.between_episode_timeout):
                    return

    def refresh_dub_sub_for_service(self, service, mdnx_api, current_queue):
        logger.info(f"[MainLoop] Checking if already existing episodes have new dubs/subs from {service}...")

        bucket = current_queue.get(service, {})

        wanted_dubs = set()
        for lang in config["mdnx"]["cli-defaults"]["dubLang"]:
            wanted_dubs.add(lang.lower())

        wanted_subs = set()
        for lang in config["mdnx"]["cli-defaults"]["dlsubs"]:
            wanted_subs.add(lang.lower())

        logger.info("[MainLoop] Verifying language tracks in downloaded files.")
        for series_id, season_key, episode_key, season_info, episode_info in iter_episodes(bucket):

            file_path = get_episode_file_path(bucket, series_id, season_key, episode_key, DATA_DIR)
            episode_basename = os.path.basename(file_path)
            if not os.path.exists(file_path):
                continue

            local_dubs, local_subs = probe_streams(file_path, config["app"]["CHECK_MISSING_DUB_SUB_TIMEOUT"])

            derived = set(local_subs)
            for loc in list(local_subs):
                if "-" in loc:
                    derived.add(loc.split("-")[0])  # turn things like "en-in" to "en"
            local_subs = derived

            missing_dubs = wanted_dubs - local_dubs
            missing_subs = wanted_subs - local_subs

            if not missing_dubs and not missing_subs:
                logger.info(f"[MainLoop] {episode_basename} is up to date. All requested dubs and subs are present locally. No download needed.")
                continue

            avail_dubs = set()
            for dub in episode_info.get("available_dubs", []):
                avail_dubs.add(dub.lower())

            avail_subs = set()
            for sub in episode_info.get("available_subs", []):
                avail_subs.add(sub.lower())

            # only consider missing tracks that streaming service can actually provide
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
                logger.info(f"[MainLoop] Skipping re-download for {episode_basename}: requested tracks are missing locally but not offered by {service} yet.")
                continue

            if effective_missing_dubs:
                logger.info(f"[MainLoop] Missing dubs detected for {episode_basename}: {', '.join(effective_missing_dubs)}. Re-downloading episode to acquire missing dubs.")

            if effective_missing_subs:
                logger.info(f"[MainLoop] Missing subs detected for {episode_basename}: {', '.join(effective_missing_subs)}. Re-downloading episode to acquire missing subs.")

            dub_override = select_dubs(episode_info)

            if mdnx_api.download_episode(series_id, season_info["season_id"], episode_info["episode_number_download"], dub_override):
                temp_path = os.path.join(TEMP_DIR, "output.mkv")
                if file_manager.transfer(temp_path, file_path, overwrite=True):
                    logger.info("[MainLoop] Transfer complete.")
                    series_name = bucket[series_id]["series"]["series_name"]
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

    def mainloop(self) -> None:
        try:
            while not self.stop_event.is_set():
                logger.debug("[MainLoop] Executing main loop task.")
                refresh_ok = self.refresh_queue()
                if not refresh_ok:
                    self.stop()
                    return

                current_queue = queue_manager.output()

                if config["app"]["ONLY_CREATE_QUEUE"] == True:
                    logger.info("[MainLoop] ONLY_CREATE_QUEUE is True. Exiting after queue creation.\nIf docker-compose.yaml has 'restart: always/unless-stopped', please change it to 'restart: no' to prevent restart loop.")
                    self.stop()
                    return

                # download any missing / not yet downloaded episodes for Crunchyroll
                if self.cr_enabled:
                    self.download_for_service("Crunchyroll", self.cr_mdnx_api, current_queue)

                    # Check for missing dubs and subs in downloaded files for Crunchyroll series
                    if self.check_missing_dub_sub == True:
                        self.refresh_dub_sub_for_service("Crunchyroll", self.cr_mdnx_api, current_queue)
                    else:
                        logger.info("[MainLoop] CHECK_MISSING_DUB_SUB is False. Skipping dub/sub verification for Crunchyroll.")

                # download any missing / not yet downloaded episodes for HiDive
                if self.hidive_enabled:
                    self.download_for_service("HiDive", self.hidive_mdnx_api, current_queue)

                    # Check for missing dubs and subs in downloaded files for HiDive series
                    if self.check_missing_dub_sub == True:
                        self.refresh_dub_sub_for_service("HiDive", self.hidive_mdnx_api, current_queue)
                    else:
                        logger.info("[MainLoop] CHECK_MISSING_DUB_SUB is False. Skipping dub/sub verification for HiDive.")

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
                if len(self.notifications_buffer) > 0 and config["app"]["MEDIASERVER_TYPE"] is not None:
                    logger.info("[MainLoop] Triggering media server scan.")
                    mediaserver_scan_library()

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
