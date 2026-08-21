import os
import re
import json
import subprocess
import threading

from appdata.modules.Globals import queue_manager, log_manager
from appdata.modules.API.CardinalDL._shared import (
    CDL_SERVICE_BIN_PATH,
    normalize_audio_qualities, normalize_subtitles, normalize_video_qualities
)
from appdata.modules.Vars import (
    config,
    TEMP_DIR,
    apply_series_blacklist, get_season_monitor_config, sanitize
)
from appdata.modules.types.queue import Episode, Season, Series, SeriesInfo
from appdata.modules.Globals import remote_specials


class HIDIVE_CDL_API:
    def __init__(self) -> None:
        self.cdl_path = CDL_SERVICE_BIN_PATH
        self.cdl_working_dir = os.path.dirname(self.cdl_path)
        self.cdl_service = "hidive"
        self.queue_service = "cdl-hidive"
        self.service_config = config.cardinaldl.hidive
        self.download_filename = os.path.join(self.service_config.dlpath, "output.mkv")
        self.download_thread = None
        self.download_proc = None
        self.download_lock = threading.Lock()
        self.json_path = os.path.join(TEMP_DIR, "output.json")

        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            log_manager.debug("Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            log_manager.debug("stdbuf not found, using default command without buffering.")

        log_manager.info(f"CardinalDL API initialized with: Path: {self.cdl_path} | Service: {self.cdl_service}")

        # Titles like "E7 - Coming 5/19/26 13:30 UTC", "TBA", etc (after stripping the "E# - " prefix).
        self.unreleased_title_flag = re.compile(r'^\s*(coming|tba|tbd|available\s+on|premieres?|releasing)\b', re.IGNORECASE)
        self.episode_prefix_strip = re.compile(r'^\s*E\d+(?:\.\d+)?\s*-\s*', re.IGNORECASE)

    def start_monitor(self, series_id: str) -> str:
        """Load a full series payload and add it to the queue."""

        log_manager.debug(f"Monitoring series with ID: {series_id}")

        if os.path.isfile(self.json_path):
            os.remove(self.json_path)

        tmp_cmd = [self.cdl_path, "--service", self.cdl_service, "--srz", series_id, "--full", "--workers", "3", "--jsonoutput", self.json_path, "--configpath", self.service_config.configpath]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.cdl_working_dir)
        log_manager.debug(f"Console output for start_monitor process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for start_monitor process (stderr):\n{result.stderr}")

        if result.returncode != 0:
            log_manager.error(f"CardinalDL listing failed for {series_id} with exit code {result.returncode}.")
            return result.stdout

        if not os.path.isfile(self.json_path):
            log_manager.warning(f"CardinalDL json payload not found at {self.json_path}.")
            return result.stdout

        try:
            with open(self.json_path, "r", encoding="utf-8") as file_handle:
                parsed_payload = json.load(file_handle)
        except (OSError, json.JSONDecodeError) as exc:
            log_manager.warning(f"Failed to read CardinalDL json payload at {self.json_path}: {exc}")
            return result.stdout

        self._process_json_payload(parsed_payload, requested_series_id=series_id)

        log_manager.debug(f"Monitoring for series with ID: {series_id} complete.")
        return result.stdout

    def stop_monitor(self, series_id: str) -> None:
        """Stop monitoring a series by removing it from the queue."""

        queue_manager.remove(series_id, self.queue_service)
        log_manager.debug(f"Stopped monitoring series with ID: {series_id}")
        return

    def update_monitor(self, series_id: str) -> str:
        """Refresh a full series payload and update the queue."""

        log_manager.debug(f"Updating monitor for series with ID: {series_id}")

        if os.path.isfile(self.json_path):
            os.remove(self.json_path)

        tmp_cmd = [self.cdl_path, "--service", self.cdl_service, "--srz", series_id, "--full", "--workers", "3", "--jsonoutput", self.json_path, "--configpath", self.service_config.configpath]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.cdl_working_dir)
        log_manager.debug(f"Console output for update_monitor process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for update_monitor process (stderr):\n{result.stderr}")

        if result.returncode != 0:
            log_manager.error(f"CardinalDL listing failed for {series_id} with exit code {result.returncode}.")
            return result.stdout

        if not os.path.isfile(self.json_path):
            log_manager.warning(f"CardinalDL json payload not found at {self.json_path}.")
            return result.stdout

        try:
            with open(self.json_path, "r", encoding="utf-8") as file_handle:
                parsed_payload = json.load(file_handle)
        except (OSError, json.JSONDecodeError) as exc:
            log_manager.warning(f"Failed to read CardinalDL json payload at {self.json_path}: {exc}")
            return result.stdout

        self._process_json_payload(parsed_payload, requested_series_id=series_id)

        log_manager.debug(f"Updating monitor for series with ID: {series_id} complete.")
        return result.stdout

    def cancel_active_download(self) -> None:
        """Cancel any active download process and wait for the worker thread to stop."""

        proc = None
        thread = None

        with self.download_lock:
            proc = self.download_proc
            thread = self.download_thread

        if proc is not None:
            try:
                if proc.poll() is None:
                    log_manager.info("Killing active CardinalDL download process...")
                    proc.kill()
            except Exception as e:
                log_manager.error(f"Failed to kill active CardinalDL process: {e}", exc_info=e)

        if thread is not None and thread.is_alive():
            log_manager.info("Waiting for download worker thread to exit...")
            thread.join(timeout=5.0)

        with self.download_lock:
            if self.download_thread is thread:
                self.download_thread = None

            if self.download_proc is proc:
                self.download_proc = None

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list[str] | None = None, sub_override: list[str] | None = None, video_override: str | None = None, audio_override: str | None = None) -> bool:
        """Download a specific episode using the CardinalDL service."""

        log_manager.info(f"Downloading episode {episode_number} for series {series_id} season {season_id}")

        if dub_override is False:
            log_manager.info("No dubs were found for this episode, skipping download.")
            return False

        tmp_cmd = [
            self.cdl_path,
            "--service", self.cdl_service,
            "--item", series_id,
            "--season", season_id,
            "--episode", episode_number
        ]

        if video_override:
            tmp_cmd += ["--videoquality", video_override]
            log_manager.info(f"Using videoquality override: {video_override}")

        if audio_override:
            tmp_cmd += ["--audioquality", audio_override]
            log_manager.info(f"Using audioquality override: {audio_override}")

        if self.service_config.fallback:
            tmp_cmd += ["--fallback"]
            log_manager.info("Using fallback flag.")

        # only add the hybrid flag if it is explicitly set to True or False.
        # If it is None, we leave it out and let CardinalDL's GUI settings decide.
        if self.service_config.hybrid is not None:
            hybrid_value = str(self.service_config.hybrid).lower()
            tmp_cmd += ["--hybrid", hybrid_value]
            log_manager.info(f"Using hybrid override: {hybrid_value}")

        if self.service_config.outputformat:
            tmp_cmd += ["--outputformat", self.service_config.outputformat]
            log_manager.info(f"Using outputformat override: {self.service_config.outputformat}")

        if self.service_config.dectool:
            tmp_cmd += ["--dectool", self.service_config.dectool]
            log_manager.info(f"Using dectool override: {self.service_config.dectool}")

        if dub_override:
            joined_dubs = ",".join(dub_override)
            tmp_cmd += ["--dublang", joined_dubs]
            log_manager.info(f"Using dublang override: {joined_dubs}")
        else:
            log_manager.info("No dublang override selected. Letting CardinalDL use its storage defaults.")

        if sub_override:
            joined_subs = ",".join(sub_override)
            tmp_cmd += ["--dlsubs", joined_subs]
            log_manager.info(f"Using dlsubs override: {joined_subs}")

        if self.service_config.forcesubformat:
            tmp_cmd += ["--forcesubformat", self.service_config.forcesubformat]
            log_manager.info(f"Using forcesubformat override: {self.service_config.forcesubformat}")

        tmp_cmd += ["--filename", "output"]
        tmp_cmd += ["--dlpath", self.service_config.dlpath]
        tmp_cmd += ["--temppath", self.service_config.temppath]
        tmp_cmd += ["--configpath", self.service_config.configpath]

        if self.stdbuf_exists:
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            cmd = tmp_cmd

        # dry run stops here so we can show the command without running it
        if config.app.dry_run:
            log_manager.info(f"DRY_RUN is True. Would have run: {' '.join(cmd)}")
            return False

        with self.download_lock:
            if self.download_thread and self.download_thread.is_alive():
                log_manager.error("A download is already in progress. refusing to start a second one.")
                return False

        result = {"returncode": None}

        worker = threading.Thread(
            target=self._run_download,
            args=(cmd, result),
            name=f"{self.cdl_service}-download",
            daemon=True
        )

        with self.download_lock:
            self.download_thread = worker

        worker.start()

        while worker.is_alive():
            worker.join(timeout=1.0)

        returncode = result["returncode"]

        if returncode not in (0, None):
            log_manager.error(f"Download failed with exit code {returncode}")
            return False

        if not os.path.isfile(self.download_filename):
            log_manager.error(f"Download finished, but expected output file was not found: {self.download_filename}")
            return False

        log_manager.info("Download finished successfully.")
        return True

    def _run_download(self, cmd: list, result: dict) -> None:
        """Run the download command in a worker thread and stream logs live."""

        returncode = -1
        proc = None

        try:
            log_manager.info(f"Executing command: {' '.join(cmd)}")

            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=self.cdl_working_dir
            ) as proc:
                with self.download_lock:
                    self.download_proc = proc

                if proc.stdout is not None:
                    for line in proc.stdout:
                        cleaned_line = line.rstrip()
                        log_manager.info(cleaned_line)

                returncode = proc.wait()

        except Exception as e:
            log_manager.error(f"Failed to run download: {e}", exc_info=e)

        finally:
            with self.download_lock:
                self.download_proc = None

            result["returncode"] = returncode

    def _process_json_payload(self, parsed_payload: dict, add2queue: bool = True, requested_series_id: str | None = None):
        """Convert the structured JSON payload from --jsonoutput to queue db format."""

        log_manager.debug("Processing CardinalDL JSON payload...")

        item_info = parsed_payload.get("item") or {}
        seasons_list = parsed_payload.get("seasons") or []

        series_id = str(item_info.get("id") or "").strip()
        if series_id == "":
            log_manager.warning("CardinalDL JSON payload did not include a series id.")
            return {}

        # if the caller requested a specific series id, skip any payload that doest match that id.
        if requested_series_id is not None and series_id != requested_series_id:
            log_manager.warning(f"CardinalDL returned series id '{series_id}' but '{requested_series_id}' was requested. Skipping this payload.")
            return {}

        series_title = sanitize(str(item_info.get("title") or "Unknown Series"))

        tmp_dict: dict[str, Series] = {
            series_id: Series(
                series=SeriesInfo(
                    series_name=series_title,
                    series_id=series_id
                ),
                seasons={}
            )
        }

        candidate_seasons = []

        for json_index, season_data in enumerate(seasons_list):
            season_id = str(season_data.get("id") or "").strip()
            if season_id == "":
                continue

            raw_season_number = season_data.get("season")
            fallback_title_number = raw_season_number if raw_season_number not in (None, "") else json_index + 1
            raw_season_title = str(season_data.get("title") or f"Season {fallback_title_number}")

            raw_episode_list = season_data.get("episodes") or []
            if not isinstance(raw_episode_list, list) or raw_episode_list == []:
                continue

            season_title = sanitize(raw_season_title)

            episodes_dict = {}
            kept_episode_count = 0

            for episode_data in raw_episode_list:
                # CardinalDL marks specials with is_special=True. We skip those so file numbering stays contiguous.
                if episode_data.get("is_special") == True:
                    log_manager.debug(f"Skipping special episode (title='{episode_data.get('title')}', season_id={season_id})")
                    continue

                # remote-specials override: drop using upstream season number and episode number/id
                if raw_season_number not in (None, ""):
                    override_season_key = f"S{raw_season_number}"
                    override_episode_number = str(episode_data.get("episode") or "").strip()
                    override_episode_id_raw = str(episode_data.get("id") or "").strip()
                    override_episode_id = override_episode_id_raw if override_episode_id_raw != "" else None
                    if remote_specials.is_remote_special("cardinaldl", "hidive", series_id, override_season_key, override_episode_number, episode_id=override_episode_id):
                        log_manager.debug(f"Skipping remote-special at {override_season_key}E{override_episode_number} series_id={series_id} id={override_episode_id_raw}")
                        continue

                raw_episode_number = episode_data.get("episode")
                if raw_episode_number is None or str(raw_episode_number).strip() == "":
                    raw_episode_number = kept_episode_count + 1

                episode_title = str(episode_data.get("title") or f"Episode {kept_episode_count + 1}")
                episode_title = sanitize(episode_title)
                episode_title = self.episode_prefix_strip.sub("", episode_title).strip()

                if episode_title.lstrip().lower().startswith("pv"):
                    log_manager.debug(f"Skipping PV entry in CardinalDL JSON: {episode_title}")
                    continue

                # drop unreleased episodes whose title is a placeholder like "Coming 5/19/26 13:30 UTC"
                if self.unreleased_title_flag.match(episode_title):
                    log_manager.debug(f"Skipping unreleased episode (title='{episode_title}', season_id={season_id})")
                    continue

                kept_episode_count += 1
                episode_key = f"E{kept_episode_count}"

                available_audio_qualities = normalize_audio_qualities(episode_data.get("audios") or {})
                available_dubs = list(available_audio_qualities)
                available_subs = normalize_subtitles(episode_data.get("subtitles") or [])
                available_video_qualities = normalize_video_qualities(episode_data.get("qualities") or {})

                # Pull the CardinalDL id straight from the JSON so the queue points back to the source record.
                episode_id_value = str(episode_data.get("id") or "").strip()
                if episode_id_value == "":
                    episode_id_value = None

                episodes_dict[episode_key] = Episode(
                    episode_id=episode_id_value,
                    episode_number=str(kept_episode_count),
                    episode_number_download=str(raw_episode_number),
                    episode_name=episode_title,
                    available_dubs=available_dubs,
                    available_subs=available_subs,
                    available_video_qualities=available_video_qualities,
                    available_audio_qualities=available_audio_qualities
                )

            if episodes_dict == {}:
                continue

            candidate_seasons.append({
                "season_id": season_id,
                "season_title": season_title,
                "raw_season_number": raw_season_number,
                "json_index": json_index,
                "episodes_dict": episodes_dict
            })

        def _sort_key(candidate):
            try:
                return (0, int(candidate["raw_season_number"]), candidate["json_index"])
            except (ValueError, TypeError):
                return (1, 0, candidate["json_index"])

        candidate_seasons.sort(key=_sort_key)

        for new_idx, candidate in enumerate(candidate_seasons, start=1):
            season_key = f"S{new_idx}"
            stored_season_number = str(new_idx)
            season_monitor = get_season_monitor_config(self.queue_service, series_id, candidate["season_id"])

            if season_monitor is not None and season_monitor.season_override is not None:
                stored_season_number = str(season_monitor.season_override)

            log_manager.debug(
                f"Mapped season raw='{candidate['raw_season_number']}' to S{new_idx} "
                f"(season_id={candidate['season_id']}, title='{candidate['season_title']}')"
            )

            tmp_dict[series_id].seasons[season_key] = Season(
                season_id=candidate["season_id"],
                season_number=stored_season_number,
                season_name=candidate["season_title"],
                episodes=candidate["episodes_dict"]
            )

        tmp_dict = apply_series_blacklist(tmp_dict, service=self.queue_service)

        log_manager.debug("JSON payload processed.")

        if add2queue:
            queue_manager.add(tmp_dict, self.queue_service)

        return tmp_dict
