import os
import re
import sys
import subprocess
import threading

from appdata.modules.Globals import queue_manager, log_manager
from appdata.modules.API.MDNX._shared import (
    MDNX_API_OK_LOGS, MDNX_SERVICE_BIN_PATH, LANG_MAP
)
from appdata.modules.Vars import (
    config,
    apply_series_blacklist, dedupe_casefold, get_season_monitor_config, sanitize
)
from appdata.modules.types.queue import Episode, Season, Series, SeriesInfo
from appdata.modules.Globals import extra_specials


# Language normalization map for ADN. Maps from user-facing language names to (audio_code, sub_locale) pairs.
# ADN itself only has content in french (fr), german (de), polish (pl), and japanese (ja), so we only handle those.
ADN_LANG_MAP = {
    "fr": LANG_MAP["French"],
    "de": LANG_MAP["German"],
    "pl": LANG_MAP["Polish"],
    "ja": LANG_MAP["Japanese"],
}


class ADN_MDNX_API:
    def __init__(self) -> None:
        self.mdnx_path = MDNX_SERVICE_BIN_PATH
        self.mdnx_service = "adn"
        self.queue_service = "adn"
        self.username = str(config.app.adn_username)
        self.password = str(config.app.adn_password)
        self.download_thread = None
        self.download_proc = None
        self.download_lock = threading.Lock()

        # Series header: "[S.<series_id>] <name>"
        self.series_pattern = re.compile(r'^\[S\.(?P<series_id>\d+)\]\s+(?P<series_name>.+?)\s*$')

        # Episode header: "(<episode_id>) [E<download_number>] <title>"
        self.episode_pattern = re.compile(r'^\((?P<episode_id>\d+)\)\s*\[E(?P<download_number>\d+)\]\s+(?P<episode_title>.+?)\s*$')

        # Title prefix: "Épisode N - <rest>". The N value is what we use to
        # detect a new season (resets back to 1, or to anything <= prev N).
        self.episode_title_prefix_pattern = re.compile(r'^Épisode\s+(?P<n>\d+)\s*-\s*(?P<rest>.+?)\s*$')

        # Versions and Subtitles lines under the most recent episode.
        self.versions_pattern = re.compile(r'-\s*Versions:\s*(.+)', re.IGNORECASE)
        self.subtitles_pattern = re.compile(r'-\s*Subtitles:\s*(.+)', re.IGNORECASE)

        # stdout line-buffering if available
        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            log_manager.debug("Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            log_manager.debug("stdbuf not found, using default command without buffering.")

        log_manager.info(f"MDNX API initialized with: Path: {self.mdnx_path} | Service: {self.mdnx_service}")

    def auth(self) -> str:
        """Authenticate with the MDNX service using provided credentials."""

        log_manager.info(f"Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            log_manager.error("MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nADN_USERNAME\nADN_PASSWORD\nExiting...")
            sys.exit(1)

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--auth", "--username", self.username, "--password", self.password, "--silentAuth"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        log_manager.info(f"Console output for auth process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for auth process (stderr):\n{result.stderr}")

        log_manager.info(f"Authentication with {self.mdnx_service} complete.")
        return result.stdout

    def start_monitor(self, series_id: str) -> str:
        """Starts monitoring a series by its ID using the MDNX service."""

        log_manager.debug(f"Monitoring series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "-s", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        log_manager.debug(f"Console output for start_monitor process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for start_monitor process (stderr):\n{result.stderr}")

        self._process_console_output(result.stdout)

        log_manager.debug(f"Monitoring for series with ID: {series_id} complete.")
        return result.stdout

    def stop_monitor(self, series_id: str) -> None:
        """Stops monitoring a series by its ID using the MDNX service."""

        queue_manager.remove(series_id, self.queue_service)
        log_manager.debug(f"Stopped monitoring series with ID: {series_id}")
        return

    def update_monitor(self, series_id: str) -> str:
        """Updates monitoring for a series by its ID using the MDNX service."""

        log_manager.debug(f"Updating monitor for series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "-s", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        log_manager.debug(f"Console output for update_monitor process:\n{result.stdout}")

        if result.stderr:
            log_manager.warning(f"Console output for update_monitor process (stderr):\n{result.stderr}")

        self._process_console_output(result.stdout)

        log_manager.debug(f"Updating monitor for series with ID: {series_id} complete.")
        return result.stdout

    def cancel_active_download(self) -> None:
        """Cancels any active download process and waits for the worker thread to exit."""

        proc = None
        thread = None

        with self.download_lock:
            proc = self.download_proc
            thread = self.download_thread

        # kill the process if its still running
        if proc is not None:
            try:
                if proc.poll() is None:
                    log_manager.info("Killing active mdnx download process...")
                    proc.kill()
            except Exception as e:
                log_manager.error(f"Failed to kill active mdnx process: {e}")

        # wait a bit for the worker thread to exit
        if thread is not None and thread.is_alive():
            log_manager.info("Waiting for download worker thread to exit...")
            thread.join(timeout=5.0)

        # clear handles
        with self.download_lock:
            if self.download_thread is thread:
                self.download_thread = None
            if self.download_proc is proc:
                self.download_proc = None

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list[str] | None = None, sub_override: list[str] | None = None) -> bool:
        """Downloads a specific episode using the MDNX service."""

        log_manager.info(f"Downloading episode {episode_number} for series {series_id} season {season_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "-s", series_id, "-e", episode_number]

        if dub_override is False:
            log_manager.info("No dubs were found for this episode, skipping download.")
            return False

        if dub_override:
            tmp_cmd += ["--dubLang", *dub_override]
            log_manager.info(f"Using dubLang override: {' '.join(dub_override)}")

        if sub_override:
            tmp_cmd += ["--dlsubs", *sub_override]
            log_manager.info(f"Using dlsubs override: {' '.join(sub_override)}")

        # Hardcoded options.
        # These can not be modified by config.json, or things will break/not work as expected.
        tmp_cmd += ["--fileName", "output"]
        tmp_cmd += ["--skipUpdate", "true"]

        if self.stdbuf_exists:
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            cmd = tmp_cmd

        # make sure we dont start two downloads at once
        with self.download_lock:
            if self.download_thread and self.download_thread.is_alive():
                log_manager.error("A download is already in progress. refusing to start a second one.")
                return False

        result = {"success": False, "returncode": None}

        worker = threading.Thread(
            target=self._run_download,
            args=(cmd, result),
            name=f"{self.mdnx_service}-download",
            daemon=True,
        )

        with self.download_lock:
            self.download_thread = worker

        worker.start()

        # wait for download to finish
        while worker.is_alive():
            worker.join(timeout=1.0)

        # retrieve results
        rc = result["returncode"]
        success = result["success"]

        if rc not in (0, None):
            log_manager.error(f"Download failed with exit code {rc}")
            return False

        if not success:
            log_manager.error("Download did not report successful download. Assuming failure.")
            return False

        log_manager.info("Download finished successfully.")
        return True

    def _run_download(self, cmd: list, result: dict) -> None:
        """Internal method to run the download command in a separate thread and capture its output."""

        success = False
        returncode = -1
        proc = None

        try:
            log_manager.info(f"Executing command: {' '.join(cmd)}")

            with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
                with self.download_lock:
                    self.download_proc = proc

                for line in proc.stdout:
                    cleaned = line.rstrip()
                    log_manager.info(cleaned)

                    if any(ok_log.lower() in cleaned.lower() for ok_log in MDNX_API_OK_LOGS):
                        success = True

                returncode = proc.returncode

        except Exception as e:
            log_manager.error(f"Download crashed with exception: {e}")

        finally:

            with self.download_lock:
                self.download_proc = None

            result["success"] = success
            result["returncode"] = returncode

    def _process_console_output(self, output: str, add2queue: bool = True):
        """Parse the console output from MDNX CLI and build structured series/season/episode data."""

        log_manager.debug("Processing console output...")
        tmp_dict: dict[str, Series] = {}
        current_series_id = None

        current_season_index = 1
        current_season_episodes = []
        prev_episode_n = None
        current_episode_record = None
        total_episodes_for_series = 0

        def _flush_season():
            """Flush the in-flight episode list as a Season under the current season index."""

            nonlocal current_season_episodes, total_episodes_for_series

            if not current_season_episodes:
                return

            # season_id is the same value as series_id because ADN doesnt have series IDs...i think.
            season_id = current_series_id
            season_key = f"S{current_season_index}"

            episodes_dict: dict[str, Episode] = {}
            for local_index, record in enumerate(current_season_episodes, start=1):
                episode_key = f"E{local_index}"
                if record["title"]:
                    episode_name = sanitize(record["title"])
                else:
                    episode_name = f"Episode {local_index}"

                episodes_dict[episode_key] = Episode(
                    episode_id=record["episode_id"],
                    episode_number=str(local_index),
                    episode_number_download=str(record["download_number"]),
                    episode_name=episode_name,
                    available_dubs=record["available_dubs"],
                    available_subs=record["available_subs"],
                )
                total_episodes_for_series += 1

            # honor user season_override from adn_monitor_series_id if set.
            stored_season_number = str(current_season_index)
            season_monitor = get_season_monitor_config("adn", current_series_id, season_id)
            if season_monitor is not None and season_monitor.season_override is not None:
                stored_season_number = str(season_monitor.season_override)

            tmp_dict[current_series_id].seasons[season_key] = Season(
                season_id=season_id,
                season_name=sanitize(f"Season {current_season_index}"),
                season_number=stored_season_number,
                episodes=episodes_dict,
            )

            current_season_episodes = []

        def _finalize_series():
            """Fill in seasons_count and eps_count on the current series."""

            if current_series_id is None:
                return
            if current_series_id not in tmp_dict:
                return

            series_obj = tmp_dict[current_series_id]
            series_obj.series.seasons_count = str(len(series_obj.seasons))
            series_obj.series.eps_count = str(total_episodes_for_series)

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("[ERROR]") or line.startswith("[WARN]"):
                # ignore tool diagnostics printed in the stream
                continue
            if all(ch == "-" for ch in line):
                # ADN prints a separator line of dashes after the listing.
                continue

            # Series header
            series_match = self.series_pattern.match(line)
            if series_match:
                # finish the previous series before switching
                _flush_season()
                _finalize_series()

                groupdict = series_match.groupdict()
                current_series_id = groupdict["series_id"]
                tmp_dict[current_series_id] = Series(
                    series=SeriesInfo(
                        series_name=sanitize(groupdict["series_name"]),
                        series_id=groupdict["series_id"],
                    ),
                    seasons={},
                )

                current_season_index = 1
                current_season_episodes = []
                prev_episode_n = None
                current_episode_record = None
                total_episodes_for_series = 0
                continue

            if not current_series_id:
                # ignore noise before the first series header
                continue

            # Episode header
            episode_match = self.episode_pattern.match(line)
            if episode_match:
                groupdict = episode_match.groupdict()
                episode_id = groupdict["episode_id"]
                download_number = int(groupdict["download_number"])
                raw_title = groupdict["episode_title"]

                # Pull the "Episode N - " prefix off the title to drive season-boundary detection.
                # If the title does not have the prefix, fall back so we never trigger a false reset.
                prefix_match = self.episode_title_prefix_pattern.match(raw_title)
                if prefix_match:
                    n_value = int(prefix_match.group("n"))
                    clean_title = prefix_match.group("rest")
                else:
                    log_manager.warning(f"ADN episode title missing 'Episode N - ' prefix: {raw_title!r}")
                    if prev_episode_n is None:
                        n_value = 1
                    else:
                        n_value = prev_episode_n + 1
                    clean_title = raw_title

                # title number reset to a smaller (or equal) value than the previous episode.
                # Equal handles a one-episode season followed by another one-episode season.
                if prev_episode_n is not None and n_value <= prev_episode_n:
                    log_manager.debug(f"ADN season reset: prev N={prev_episode_n}, new N={n_value}, advancing to S{current_season_index + 1}")
                    _flush_season()
                    current_season_index += 1

                # Check if this episode is marked in the extra-specials list.
                # If so, skip it entirely.
                season_key = f"S{current_season_index}"
                if extra_specials.is_extra_special("mdnx", "adn", current_series_id, season_key, str(download_number), episode_id=episode_id):
                    log_manager.debug(f"Skipping extra-special at {season_key}E{download_number} series_id={current_series_id} id={episode_id}")
                    current_episode_record = None
                    continue

                record = {
                    "episode_id": episode_id,
                    "download_number": download_number,
                    "title": clean_title,
                    "available_dubs": [],
                    "available_subs": [],
                }
                current_season_episodes.append(record)
                current_episode_record = record
                prev_episode_n = n_value
                continue

            # Versions line attaches to the most recent episode record.
            versions_match = self.versions_pattern.match(line)
            if versions_match and current_episode_record is not None:
                raw_list = versions_match.group(1)

                dub_codes = []
                for token in self._clean_tokens(raw_list):
                    pair = self._norm_lang(token)
                    if pair is not None:
                        dub_codes.append(pair[0])

                current_episode_record["available_dubs"] = dedupe_casefold(dub_codes)
                continue

            # Subtitles line attaches to the most recent episode record.
            subtitles_match = self.subtitles_pattern.match(line)
            if subtitles_match and current_episode_record is not None:
                raw_list = subtitles_match.group(1)

                sub_locales = []
                for token in self._clean_tokens(raw_list):
                    pair = self._norm_lang(token)
                    if pair is not None:
                        sub_locales.append(pair[1])

                current_episode_record["available_subs"] = dedupe_casefold(sub_locales)
                continue

        # Flush the in-flight season and finalize the in-flight series.
        _flush_season()
        _finalize_series()

        if current_series_id is None:
            log_manager.warning("No ADN series detected in output.")
            if add2queue:
                queue_manager.add(tmp_dict, self.queue_service)
            return tmp_dict

        # apply per-series blacklist to mark episodes to skip
        tmp_dict = apply_series_blacklist(tmp_dict, service="adn")

        log_manager.debug("Console output processed.")
        if add2queue:
            queue_manager.add(tmp_dict, self.queue_service)
        return tmp_dict

    def _clean_tokens(self, text: str):
        """Split a comma-separated list, trim, drop empties."""

        if not text:
            return []

        tokens = []
        for token in text.split(','):
            token = token.strip()
            if token:
                tokens.append(token)

        return tokens

    def _norm_lang(self, token: str):
        """Normalize an ADN language token to (audio_code, sub_locale). Unknown returns None."""

        if not token:
            return None

        lowered = token.strip().lower()
        pair = ADN_LANG_MAP.get(lowered)

        if pair is None:
            log_manager.warning(f"ADN unknown language token: {token!r}. Skipping.")
            return None

        return pair
