import os
import re
import json
import subprocess
import threading

from appdata.modules.Globals import queue_manager, log_manager
from appdata.modules.Vars import (
    config,
    ZLO_SERVICE_BIN_PATH, normalize_zlo_dubs, normalize_zlo_subtitles, normalize_zlo_qualities,
    sanitize, apply_series_blacklist, get_season_monitor_config
)


class HIDIVE_ZLO_API:
    def __init__(self) -> None:
        self.zlo_path = ZLO_SERVICE_BIN_PATH
        self.zlo_working_dir = os.path.dirname(self.zlo_path)
        self.zlo_service = "hidive"
        self.queue_service = "zlo-hidive"
        self.service_config = config.zlo.hidive
        self.download_filename = os.path.join(self.service_config.dlpath, "output.mkv")
        self.download_thread = None
        self.download_proc = None
        self.download_lock = threading.Lock()

        # this strips the color codes from ZLO logs so JSON parsing works.
        self.ansi_escape_pattern = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            log_manager.debug("Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            log_manager.debug("stdbuf not found, using default command without buffering.")

        log_manager.info(f"ZLO API initialized with: Path: {self.zlo_path} | Service: {self.zlo_service}")

    def start_monitor(self, series_id: str) -> str:
        """Load a full series payload and add it to the queue."""

        log_manager.debug(f"Monitoring series with ID: {series_id}")

        tmp_cmd = [self.zlo_path, "--service", self.zlo_service, "--srz", series_id, "--full"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.zlo_working_dir)
        log_manager.debug(f"Console output for start_monitor process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for start_monitor process (stderr):\n{result.stderr}")

        self._process_console_output(result.stdout)

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

        tmp_cmd = [self.zlo_path, "--service", self.zlo_service, "--srz", series_id, "--full"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8", cwd=self.zlo_working_dir)
        log_manager.debug(f"Console output for update_monitor process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for update_monitor process (stderr):\n{result.stderr}")

        self._process_console_output(result.stdout)

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
                    log_manager.info("Killing active zlo download process...")
                    proc.kill()
            except Exception as e:
                log_manager.error(f"Failed to kill active zlo process: {e}")

        if thread is not None and thread.is_alive():
            log_manager.info("Waiting for download worker thread to exit...")
            thread.join(timeout=5.0)

        with self.download_lock:
            if self.download_thread is thread:
                self.download_thread = None

            if self.download_proc is proc:
                self.download_proc = None

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list[str] | None = None, sub_override: list[str] | None = None) -> bool:
        """Download a specific episode using the ZLO service."""

        log_manager.info(f"Downloading episode {episode_number} for series {series_id} season {season_id}")

        if dub_override is False:
            log_manager.info("No dubs were found for this episode, skipping download.")
            return False

        if not dub_override:
            log_manager.info("No dubLang values were selected for this episode, skipping download.")
            return False

        tmp_cmd = [
            self.zlo_path,
            "--service", self.zlo_service,
            "--item", series_id,
            "--season", season_id,
            "--episode", episode_number,
        ]

        quality_value = self.service_config.q.strip()
        if quality_value != "":
            tmp_cmd += ["--q", quality_value]
            log_manager.info(f"Using --q override: {quality_value}")

        tmp_cmd += ["--qf", str(self.service_config.qf).lower()]
        log_manager.info(f"Using qf override: {str(self.service_config.qf).lower()}")

        joined_dubs = ",".join(dub_override)
        tmp_cmd += ["--dubLang", joined_dubs]
        log_manager.info(f"Using dubLang override: {joined_dubs}")

        if sub_override:
            joined_subs = ",".join(sub_override)
            tmp_cmd += ["--dlsubs", joined_subs]
            log_manager.info(f"Using dlsubs override: {joined_subs}")

        tmp_cmd += ["--fileName", "output"]
        tmp_cmd += ["--dlpath", self.service_config.dlpath]
        tmp_cmd += ["--tempPath", self.service_config.tempPath]
        tmp_cmd += ["--full"]

        if self.stdbuf_exists:
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            cmd = tmp_cmd

        with self.download_lock:
            if self.download_thread and self.download_thread.is_alive():
                log_manager.error("A download is already in progress. refusing to start a second one.")
                return False

        result = {"returncode": None}

        worker = threading.Thread(
            target=self._run_download,
            args=(cmd, result),
            name=f"{self.zlo_service}-download",
            daemon=True,
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
                cwd=self.zlo_working_dir
            ) as proc:
                with self.download_lock:
                    self.download_proc = proc

                if proc.stdout is not None:
                    for line in proc.stdout:
                        cleaned_line = line.rstrip()
                        log_manager.info(cleaned_line)

                returncode = proc.wait()

        except Exception as e:
            log_manager.error(f"Download crashed with exception: {e}")

        finally:
            with self.download_lock:
                self.download_proc = None

            result["returncode"] = returncode

    def _process_console_output(self, output: str, add2queue: bool = True):
        """Find the JSON payload in the console output and convert it to queue.json format."""

        log_manager.debug("Processing console output...")

        parsed_payload = self._extract_json_payload(output)
        if not isinstance(parsed_payload, dict):
            log_manager.warning("Could not find a valid JSON payload in ZLO console output.")
            return {}

        item_info = parsed_payload.get("item") or {}
        seasons_list = parsed_payload.get("seasons") or []

        series_id = str(item_info.get("id") or "").strip()
        if series_id == "":
            log_manager.warning("ZLO JSON payload did not include a series id.")
            return {}

        series_title = sanitize(str(item_info.get("title") or "Unknown Series"))

        tmp_dict = {
            series_id: {
                "series": {
                    "series_id": series_id,
                    "series_name": series_title,
                    "seasons_count": "0",
                    "eps_count": "0",
                },
                "seasons": {}
            }
        }

        total_episode_count = 0
        candidate_seasons = []

        for json_index, season_data in enumerate(seasons_list):
            season_id = str(season_data.get("id") or "").strip()
            if season_id == "":
                continue

            raw_episode_list = season_data.get("episodes") or []
            if not isinstance(raw_episode_list, list) or raw_episode_list == []:
                continue

            raw_season_number = season_data.get("season")
            fallback_title_number = raw_season_number if raw_season_number not in (None, "") else json_index + 1
            season_title = str(season_data.get("title") or f"Season {fallback_title_number}")
            season_title = sanitize(season_title)

            episodes_dict = {}
            kept_episode_count = 0

            for episode_data in raw_episode_list:
                raw_episode_number = episode_data.get("episode")

                # ZLO marks special episodes with a null episode number (as far as i've seen)
                # so skip those to avoid confusion and maintain contiguous numbering of regular episodes.
                if raw_episode_number is None:
                    log_manager.debug(f"Skipping special episode with null episode number (title='{episode_data.get('title')}', season_id={season_id})")
                    continue

                if str(raw_episode_number).strip() == "":
                    raw_episode_number = kept_episode_count + 1

                episode_title = str(episode_data.get("title") or f"Episode {kept_episode_count + 1}")
                episode_title = sanitize(episode_title)

                if episode_title.lstrip().lower().startswith("pv"):
                    log_manager.debug(f"Skipping PV entry in ZLO JSON: {episode_title}")
                    continue

                kept_episode_count += 1
                episode_key = f"E{kept_episode_count}"

                available_dubs = normalize_zlo_dubs(episode_data.get("dubs") or [])
                available_subs = normalize_zlo_subtitles(episode_data.get("subtitles") or [])
                available_qualities = normalize_zlo_qualities(episode_data.get("qualities") or [])

                episodes_dict[episode_key] = {
                    "episode_number": str(kept_episode_count),
                    "episode_number_download": str(raw_episode_number),
                    "episode_name": episode_title,
                    "available_dubs": available_dubs,
                    "available_subs": available_subs,
                    "available_qualities": available_qualities,
                    "episode_downloaded": False,
                    "episode_skip": False,
                    "has_all_dubs_subs": False,
                }

                total_episode_count += 1

            if episodes_dict == {}:
                continue

            candidate_seasons.append({
                "season_id": season_id,
                "season_title": season_title,
                "raw_season_number": raw_season_number,
                "json_index": json_index,
                "episodes_dict": episodes_dict,
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

            tmp_dict[series_id]["seasons"][season_key] = {
                "season_id": candidate["season_id"],
                "season_name": candidate["season_title"],
                "season_number": stored_season_number,
                "episodes": candidate["episodes_dict"],
                "eps_count": str(len(candidate["episodes_dict"])),
            }

        tmp_dict[series_id]["series"]["seasons_count"] = str(len(tmp_dict[series_id]["seasons"]))
        tmp_dict[series_id]["series"]["eps_count"] = str(total_episode_count)

        tmp_dict = apply_series_blacklist(tmp_dict, service=self.queue_service)

        log_manager.debug("Console output processed.")

        if add2queue:
            queue_manager.add(tmp_dict, self.queue_service)

        return tmp_dict

    def _extract_json_payload(self, output: str):
        """Find the last full JSON object in the console output."""

        cleaned_output = self.ansi_escape_pattern.sub("", output)
        json_decoder = json.JSONDecoder()

        parsed_payload = None

        for start_index, character in enumerate(cleaned_output):
            if character != "{":
                continue

            try:
                candidate_payload, parsed_length = json_decoder.raw_decode(cleaned_output[start_index:])
            except json.JSONDecodeError:
                continue

            trailing_text = cleaned_output[start_index + parsed_length:].strip()
            if trailing_text == "":
                parsed_payload = candidate_payload
                break

        return parsed_payload
