import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .MediaServerManager import mediaserver_scan_library
from .Globals import file_manager, queue_manager, log_manager, remote_specials
from .ServiceHelper import get_wanted_dubs_and_subs, probe_streams, select_dubs, select_subs
from .Vars import (
    config,
    JELLY_CONFIGURED, PLEX_CONFIGURED, SERVICES, TEMP_DIR, TZ,
    format_duration, get_episode_file_path, get_season_monitor_config, iter_episodes
)
from .types.queue import Episode, ServiceBucket


class MainLoop:
    def __init__(self, notifier) -> None:

        self.notifier = notifier

        self.check_missing_dub_sub = config.app.check_missing_dub_sub
        self.loop_timeout = config.app.check_for_updates_interval
        self.between_episode_timeout = config.app.episode_dl_delay
        self.only_create_queue = config.app.only_create_queue
        self.skip_queue_refresh = config.app.skip_queue_refresh
        self.dry_run = config.app.dry_run
        self.notifications_buffer = []
        self.stop_requested = False

        log_manager.debug("MainLoop initialized.")

    def mainloop(self) -> None:
        try:
            while not self.stop_requested:
                log_manager.debug("Executing MainLoop task.")

                # pull the latest remote-specials.yaml and rebuild internal state for overrides.
                remote_specials.refresh()

                if self.skip_queue_refresh is True:
                    log_manager.info("SKIP_QUEUE_REFRESH is True. Skipping queue refresh step and using old queue data.")
                else:
                    self._refresh_queue()

                if self.only_create_queue == True:
                    log_manager.info("ONLY_CREATE_QUEUE is True. Exiting after queue creation.\nIf docker-compose.yaml has 'restart: always/unless-stopped', please change it to 'restart: no' to prevent restart loop.")
                    self.stop()
                    return

                # Download any missing / not yet downloaded episodes for every enabled service.
                # then (if configured) check for missing dubs/subs on already downloaded episodes.
                for service in SERVICES.all():
                    if not service.configured:
                        continue

                    self._download_for_service(service.service_name, service.display_name, service.api)

                    if self.check_missing_dub_sub == True:
                        self._refresh_dub_sub_for_service(service.service_name, service.display_name, service.api)
                    else:
                        log_manager.info(f"CHECK_MISSING_DUB_SUB is False. Skipping dub/sub verification for {service.display_name}.")

                if self.dry_run:
                    log_manager.info("DRY_RUN is True. Exiting after one iteration of the main loop.\nIf docker-compose.yaml has 'restart: always/unless-stopped', please change it to 'restart: no' to prevent restart loop.")
                    self.stop()
                    return

                # trigger media server scan if configured and there are new items in the notifications buffer.
                if len(self.notifications_buffer) > 0 and (PLEX_CONFIGURED is True or JELLY_CONFIGURED is True):
                    log_manager.info("Triggering media server scan.")
                    mediaserver_scan_library()

                if self.notifications_buffer:
                    log_manager.info("Flushing notifications buffer.")
                    self._flush_notifications()

                # wait for self.loop_timeout seconds or exit early if stop is requested.
                log_manager.info(f"MainLoop iteration completed. Next iteration in {format_duration(self.loop_timeout)} ({(datetime.now(ZoneInfo(TZ)) + timedelta(seconds=self.loop_timeout)).strftime('%I:%M:%S %p')}).")
                if self._wait_or_interrupt(timeout=self.loop_timeout):
                    return
        finally:
            log_manager.info("MainLoop exited.")

    def stop(self) -> None:
        """Signal the main loop to stop."""

        log_manager.info("Stopping MainLoop...")
        self.stop_requested = True

        # cancel any active downloads on every configured service
        for service in SERVICES.all():
            if service.configured:
                service.api.cancel_active_download()

        log_manager.info("MainLoop stop requested.")
        return

    def _wait_or_interrupt(self, timeout: int) -> bool:
        """Wait for the specified timeout or exit early if stop is requested."""

        end = time.time() + timeout
        while not self.stop_requested and time.time() < end:
            time.sleep(1)

        if self.stop_requested:
            log_manager.info("Interrupt requested. Exiting wait early.")
            return True

        return False

    def _snapshot_episode(
        self,
        series_name: str,
        episode: Episode,
        file_path: str,
        time_taken: float,
        action_label: str,
        service: str,
        before_dubs: set | None = None,
        before_subs: set | None = None
    ) -> dict:
        """Build a dict snapshot for the notification buffer."""

        try:
            after_dubs, after_subs = probe_streams(file_path, service)
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
            "episode_name": episode.episode_name,
            "episode_number": episode.episode_number,
            "before_dubs": sorted(before_dubs),
            "before_subs": sorted(before_subs),
            "after_dubs": sorted(after_dubs),
            "after_subs": sorted(after_subs),
            "path": file_path,
            "time_taken": format_duration(int(time_taken))
        }

    def _flush_notifications(self) -> None:
        """Send out notifications for all buffered items (if enabled) and clear the buffer."""

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

        # format:
        # Download summary: 3 new, 2 updated (12:00 PM 01/01/2025)
        # or
        # Download summary (12:00 PM 01/01/2025)
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
                    f"Time taken to download: {item['time_taken']}",
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
                    f"Time taken to download: {item['time_taken']}",
                    ""
                ]
            lines.append("---------------------------")

        body = "\n".join(lines).strip()

        try:
            self.notifier.notify(subject, body)
        finally:
            self.notifications_buffer.clear()

    def _refresh_queue(self) -> None:
        """Refresh the queue and start/stop monitors as needed for each configured service."""

        log_manager.info("Getting the current queue IDs...")

        for service in SERVICES.all():
            # if service not configured, dont refresh queue for said service.
            if not service.configured:
                log_manager.info(f"{service.display_name} queue refresh skipped because the service wasnt enabled.")
                continue

            monitor_ids = set(service.monitor_series_id.keys())

            # only look at the correct bucket inside queue.json for this service
            bucket = queue_manager.output(service.service_name)
            if bucket is None:
                bucket = ServiceBucket()

            queue_ids = set(bucket.series.keys())

            # if both lists are empty, nothing to do, exit early
            if not monitor_ids and not queue_ids:
                log_manager.info(f"Your '{service.monitor_config_key}' list is empty. Skipped refreshing empty list.")
                continue

            log_manager.info(f"Checking {service.display_name} monitors...")
            for series_id in monitor_ids:
                if series_id not in queue_ids:
                    log_manager.info(f"[{service.display_name}] Starting monitor for {series_id}")
                    service.api.start_monitor(series_id)
                else:
                    log_manager.info(f"[{service.display_name}] Updating monitor for {series_id}")
                    service.api.update_monitor(series_id)

            # stop monitors for series removed from config so they are no longer monitored
            log_manager.info(f"Checking {service.display_name} monitors to stop...")
            for series_id in queue_ids:
                if series_id not in monitor_ids:
                    log_manager.info(f"[{service.display_name}] Stopping monitor for {series_id}")
                    service.api.stop_monitor(series_id)

            log_manager.info(f"{service.display_name} monitor refresh complete.")

        log_manager.info("Queue refresh complete.")

    def _download_for_service(self, service: str, service_label: str, mdnx_api) -> None:
        """Download missing episodes for the specified service."""

        if self.stop_requested:
            log_manager.info(f"Stop requested. Skipping download for {service_label}.")
            return

        log_manager.info(f"Checking for episodes to download from {service_label}...")

        bucket = queue_manager.output(service)
        if bucket is None:
            return

        service_obj = SERVICES.get(service)

        for series_id, season_key, episode_key, season, episode in iter_episodes(bucket):

            if self.stop_requested:
                log_manager.info(f"Stop requested. Skipping download for {service_label}.")
                return

            file_path = get_episode_file_path(bucket, series_id, season_key, episode_key, service_obj)
            episode_basename = os.path.basename(file_path)

            if episode.episode_skip:
                log_manager.info(f"{episode_basename} is blacklisted (episode_skip=True). Skipping download.")
                continue

            if episode.episode_downloaded:
                log_manager.info(f"{episode_basename} is marked as already downloaded (episode_downloaded=True). Skipping download.")
                continue

            log_manager.info(f"Checking for {episode_basename} at {file_path}.")

            if os.path.exists(file_path):
                log_manager.info(f"Episode already exists at {file_path}. Updating 'episode_downloaded' status to True and skipping download.")
                queue_manager.update_episode_status(series_id, season_key, episode_key, True, service)
                continue

            if self.dry_run:
                log_manager.info(f"DRY_RUN is True. Would have downloaded episode for {series_id} season {season_key} episode {episode_key} that would have been stored at {file_path}.\nSkipping actual download.")
                continue

            log_manager.info(f"Episode not found at {file_path} and 'episode_downloaded' status is False. Initiating download.")

            season_monitor = get_season_monitor_config(service, series_id, season.season_id)

            dub_overrides = None
            sub_overrides = None
            if season_monitor is not None:
                dub_overrides = season_monitor.dub_overrides
                sub_overrides = season_monitor.sub_overrides

            dub_override = select_dubs(service, episode, dub_overrides)
            sub_override = select_subs(service, episode, sub_overrides)

            dl_start = time.perf_counter()
            download_episode_number = episode.episode_number_download or episode.episode_number
            download_successful = mdnx_api.download_episode(
                series_id, season.season_id, download_episode_number, dub_override, sub_override
            )
            dl_end = time.perf_counter()
            dl_elapsed = dl_end - dl_start

            if download_successful:
                temp_path = os.path.join(TEMP_DIR, "output.mkv")

                if file_manager.transfer(temp_path, file_path):
                    log_manager.info("Transfer complete.")
                    queue_manager.update_episode_status(series_id, season_key, episode_key, True, service)
                    series_name = bucket.series[series_id].series.series_name
                    snapshot = self._snapshot_episode(
                        series_name, episode, file_path, dl_elapsed, "new", service
                    )
                    self.notifications_buffer.append(snapshot)
                else:
                    log_manager.error("Transfer failed.")
                    queue_manager.update_episode_status(series_id, season_key, episode_key, False, service)
            else:
                log_manager.error(f"Episode download failed for {series_id} season {season_key} - {episode_key}.")
                queue_manager.update_episode_status(series_id, season_key, episode_key, False, service)

            file_manager.remove_temp_files()
            log_manager.info(f"Waiting for {format_duration(self.between_episode_timeout)} before next iteration.")
            if self._wait_or_interrupt(timeout=self.between_episode_timeout):
                return

    def _refresh_dub_sub_for_service(self, service: str, service_label: str, mdnx_api) -> None:
        """Probe existing files for missing dubs/subs and re-download as needed."""

        if self.stop_requested:
            log_manager.info(f"Stop requested. Skipping dub/sub verification for {service_label}.")
            return

        log_manager.info(f"Checking if already existing episodes have new dubs/subs from {service_label}...")

        bucket = queue_manager.output(service)
        if bucket is None:
            return

        service_obj = SERVICES.get(service)

        for series_id, season_key, episode_key, season, episode in iter_episodes(bucket):

            if self.stop_requested:
                log_manager.info(f"Stop requested. Skipping dub/sub verification for {service_label}.")
                return

            season_monitor = get_season_monitor_config(service, series_id, season.season_id)

            season_has_track_overrides = False
            if season_monitor is not None and (season_monitor.dub_overrides is not None or season_monitor.sub_overrides is not None):
                season_has_track_overrides = True

            file_path = get_episode_file_path(bucket, series_id, season_key, episode_key, service_obj)
            episode_basename = os.path.basename(file_path)

            if episode.episode_skip:
                log_manager.info(f"{episode_basename} is blacklisted (episode_skip=True). Skipping dub/sub check for this episode.")
                continue

            if episode.has_all_dubs_subs and season_has_track_overrides is False:
                log_manager.info(f"{episode_basename} already marked as having all requested dubs/subs (has_all_dubs_subs=True). Skipping dub/sub check for this episode.")
                continue

            if not os.path.exists(file_path):
                continue

            wanted_dubs, wanted_subs = get_wanted_dubs_and_subs(service, series_id, season.season_id)

            local_dubs, local_subs = probe_streams(file_path, service)

            derived = set(local_subs)
            for loc in list(local_subs):
                if "-" in loc:
                    derived.add(loc.split("-")[0])
            local_subs = derived

            missing_dubs = wanted_dubs - local_dubs
            missing_subs = wanted_subs - local_subs

            if not missing_dubs and not missing_subs:
                log_manager.info(f"{episode_basename} is up to date. All requested dubs and subs are locally present. No download needed.")
                queue_manager.update_episode_has_all_dubs_subs(series_id, season_key, episode_key, True, service)
                continue

            avail_dubs = set()
            for dub in episode.available_dubs:
                avail_dubs.add(dub.lower())

            avail_subs = set()
            for sub in episode.available_subs:
                avail_subs.add(sub.lower())

            effective_missing_dubs = set()
            for dub in missing_dubs:
                if dub.lower() in avail_dubs:
                    effective_missing_dubs.add(dub)

            effective_missing_subs = set()
            for sub in missing_subs:
                if sub.lower() in avail_subs:
                    effective_missing_subs.add(sub)

            skip_download = False
            if not effective_missing_dubs and not effective_missing_subs:
                skip_download = True

            log_manager.debug(
                f"{episode_basename}\ndubs: "
                f"wanted={','.join(wanted_dubs) or 'None'} "
                f"present={','.join(local_dubs) or 'None'} "
                f"available={','.join(avail_dubs) or 'None'} "
                f"downloading={','.join(effective_missing_dubs) or 'None'}\n"
                f"subs: wanted={','.join(wanted_subs) or 'None'} "
                f"present={','.join(local_subs) or 'None'} "
                f"available={','.join(avail_subs) or 'None'} "
                f"downloading={','.join(effective_missing_subs) or 'None'}\n"
            )

            if self.dry_run:
                log_manager.info(f"DRY_RUN is True. Would have re-downloaded episode for {episode_basename} to acquire missing tracks: dubs={','.join(effective_missing_dubs) or 'None'}, subs={','.join(effective_missing_subs) or 'None'}.\nSkipping actual download.")
                continue

            if skip_download:
                log_manager.info(f"Skipping re-download for {episode_basename}: requested tracks are missing locally but not offered by {service_label} yet.")
                continue

            if effective_missing_dubs:
                log_manager.info(f"Missing dubs detected for {episode_basename}: {', '.join(effective_missing_dubs)}. Re-downloading episode to acquire missing dubs.")

            if effective_missing_subs:
                log_manager.info(f"Missing subs detected for {episode_basename}: {', '.join(effective_missing_subs)}. Re-downloading episode to acquire missing subs.")

            dub_overrides = None
            sub_overrides = None
            if season_monitor is not None:
                dub_overrides = season_monitor.dub_overrides
                sub_overrides = season_monitor.sub_overrides

            dub_override = select_dubs(service, episode, dub_overrides)
            sub_override = select_subs(service, episode, sub_overrides)

            dl_start = time.perf_counter()
            download_episode_number = episode.episode_number_download or episode.episode_number
            download_successful = mdnx_api.download_episode(
                series_id, season.season_id, download_episode_number, dub_override, sub_override
            )
            dl_end = time.perf_counter()
            dl_elapsed = dl_end - dl_start

            if download_successful:
                temp_path = os.path.join(TEMP_DIR, "output.mkv")

                if file_manager.transfer(temp_path, file_path, overwrite=True):
                    log_manager.info("Transfer complete.")
                    series_name = bucket.series[series_id].series.series_name
                    snapshot = self._snapshot_episode(
                        series_name, episode, file_path, dl_elapsed, "updated", service,
                        before_dubs=local_dubs, before_subs=local_subs
                    )
                    self.notifications_buffer.append(snapshot)
                else:
                    log_manager.error("Transfer failed")
            else:
                log_manager.error("Re-download failed. Keeping existing file.")

            file_manager.remove_temp_files()
            log_manager.info(f"Waiting for {format_duration(self.between_episode_timeout)} before next iteration.")
            if self._wait_or_interrupt(timeout=self.between_episode_timeout):
                return
