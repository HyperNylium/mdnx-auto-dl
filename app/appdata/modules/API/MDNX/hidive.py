import os
import re
import sys
import subprocess
import threading

from appdata.modules.Globals import queue_manager, log_manager
from appdata.modules.Vars import (
    config,
    VALID_LOCALES, CODE_TO_LOCALE, LANG_MAP, MDNX_SERVICE_BIN_PATH, MDNX_API_OK_LOGS,
    sanitize, dedupe_casefold, apply_series_blacklist
)


class HIDIVE_MDNX_API:
    def __init__(self) -> None:
        self.mdnx_path = MDNX_SERVICE_BIN_PATH
        self.mdnx_service = "hidive"
        self.queue_service = "hidive"
        self.username = str(config.app.hidive_username)
        self.password = str(config.app.hidive_password)
        self.download_thread = None
        self.download_proc = None
        self.download_lock = threading.Lock()

        # Series, season, episode, flat-list
        self.series_pattern = re.compile(r'^\[Z\.(?P<series_id>\d+)\]\s+(?P<series_name>.+)\s+\((?P<seasons_count>\d+)\s+Seasons?\)\s*$', re.IGNORECASE)
        self.season_main_pattern = re.compile(r'^\[S\.(?P<season_id>\d+)\]\s+Season\s+(?P<season_number>\d+)(?:\s+(?P<label>[^()]+?))?\s*\((?P<eps_count>\d+)\s*(?:Episodes?|Eps?)\)\s*$', re.IGNORECASE)
        self.season_special_pattern = re.compile(r'^\[S\.(?P<season_id>\d+)\]\s+(?P<label>OVA|OAD|ONA|Specials?|Recap|Compilation|Summary|Movie|Film)(?:\s+(?P<season_number>\d+))?\s*\((?P<eps_count>\d+)\s*(?:Episodes?|Eps?)\)\s*$', re.IGNORECASE)

        # covers: "Season N OVA/Recap/... (X Episodes)"
        self.season_any_special_pattern = re.compile(
            r'^\[S\.(?P<season_id>\d+)\]\s+(?:Season\s+(?P<season_number>\d+)\s+)?'
            r'(?P<label>OVA|OAD|ONA|Specials?|Recap|Compilation|Summary|Movie|Film)'
            r'\s*\((?P<eps_count>\d+)\s*(?:Episodes?|Eps?)\)\s*$',
            re.IGNORECASE
        )
        self.episode_pattern = re.compile(r'^\[E\.(?P<episode_id>\d+)\]\s+(?P<episode_title>.+?)\s*$', re.IGNORECASE)
        self.flat_episode_pattern = re.compile(r'^\[S(?P<season_code>\d{1,3})\s*E(?P<download_number>\d{1,4}(?:\.\d+)?)\]\s+(?P<title>.+?)\s*$', re.IGNORECASE)

        # Titles like "Coming 10/10/25 15:00 UTC", "TBA", etc.
        self.unreleased_title_flag = re.compile(r'^\s*(coming|tba|tbd|available\s+on|premieres?|releasing)\b', re.IGNORECASE)

        # Probe headers
        self.audio_header = re.compile(r'(?i)\bAudio(?:s|(?:\s+Tracks)?)\s*:\s*')
        self.subs_header = re.compile(r'(?i)\bSub(?:s|titles?)\s*:\s*')

        # Special markers
        self.special_season_flag = re.compile(r'\b(OVA|OAD|ONA|Specials?|Recap|Compilation|Summary|Movie|Film)\b', re.IGNORECASE)
        self.special_episode_title_flag = re.compile(r'\b(recaps?|digest|compilation|summary|omake|extra|preview|prologue|specials?|ova|oad|ona)\b', re.IGNORECASE)

        # Display name -> (audio_code, subtitle_locale), e.g., "English" -> ("eng", "en")
        self._lang_display_to_pair = {}
        for name, pair in LANG_MAP.items():
            self._lang_display_to_pair[name.lower()] = pair

        # stdout line-buffering if available
        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            log_manager.debug("Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            log_manager.debug("stdbuf not found, using default command without buffering.")

        if config.app.hidive_skip_api_test == False:
            self.test()
        else:
            log_manager.info("API test skipped by user.")

        log_manager.info(f"MDNX API initialized with: Path: {self.mdnx_path} | Service: {self.mdnx_service}")

    def test(self) -> None:
        """Test the MDNX API by running a sample command and processing its output."""

        log_manager.info("Testing MDNX API...")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", "1244"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8").stdout
        log_manager.debug(f"MDNX API test result:\n{result}")

        json_result = self._process_console_output(result, add2queue=False)
        log_manager.info(f"Processed console output:\n{json_result}")

        # --- This needs to be researched/tested more. I am not sure what anidl outputs on auth errors with HiDive.
        # --- Leaving commented out for now. This means there will be no auto re-auth on auth errors for HiDive.
        # --- Check if the output contains authentication errors
        # error_triggers = ["invalid_grant", "Token Refresh Failed", "Authentication required", "Anonymous"]
        # if any(trigger in result for trigger in error_triggers):
        #     log_manager.info("Authentication error detected. Forcing re-authentication...")
        #     self.auth()
        # else:
        #     log_manager.info("MDNX API test successful.")

        log_manager.info("MDNX API test successful.")
        return

    def auth(self) -> str:
        """Authenticate with the MDNX service using provided credentials."""

        log_manager.info(f"Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            log_manager.error("MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nHIDIVE_USERNAME\nHIDIVE_PASSWORD\nExiting...")
            sys.exit(1)

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--auth", "--username", self.username, "--password", self.password, "--silentAuth"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        log_manager.info(f"Console output for auth process:\n{result.stdout}")

        log_manager.info(f"Authentication with {self.mdnx_service} complete.")
        return result.stdout

    def start_monitor(self, series_id: str) -> str:
        """Starts monitoring a series by its ID using the MDNX service."""

        log_manager.info(f"Monitoring series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        log_manager.debug(f"Console output for start_monitor process:\n{result.stdout}")

        self._process_console_output(result.stdout)

        log_manager.debug(f"Monitoring for series with ID: {series_id} complete.")
        return result.stdout

    def stop_monitor(self, series_id: str) -> None:
        """Stops monitoring a series by its ID using the MDNX service."""

        queue_manager.remove(series_id, self.queue_service)
        log_manager.info(f"Stopped monitoring series with ID: {series_id}")
        return

    def update_monitor(self, series_id: str) -> str:
        """Updates monitoring for a series by its ID using the MDNX service."""

        log_manager.info(f"Updating monitor for series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        log_manager.debug(f"Console output for update_monitor process:\n{result.stdout}")

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

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list | None = None) -> bool:
        """Downloads a specific episode using the MDNX service."""

        log_manager.info(f"Downloading episode {episode_number} for series {series_id} season {season_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id, "-s", season_id, "-e", episode_number]

        if dub_override is False:
            log_manager.info("No dubs were found for this episode, skipping download.")
            return False

        if dub_override:
            tmp_cmd += ["--dubLang", *dub_override]
            log_manager.info(f"Using dubLang override: {' '.join(dub_override)}")

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

        def _group_matches(count_group: int, count_declared: int) -> bool:
            """Check if a flat group size matches the declared episode count, allowing small mismatches."""

            return abs(count_group - count_declared) <= 2

        log_manager.debug("Processing console output...")
        tmp_dict = {}
        current_series_id = None
        current_season_key = None

        seasons_meta = {}          # season_key -> parsed season metadata
        episodes_by_season = {}    # season_key -> list of (episode_id, title)

        flat_groups = []           # list of {"season_code": int, "map": {local_idx -> download_number}}
        current_flat_main_code = None
        current_group_local_index = 0
        skip_current_season = False

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("[ERROR]") or line.startswith("[WARN]"):
                # ignore tool diagnostics printed in the stream
                continue

            # Series
            series_match = self.series_pattern.match(line)
            if series_match:

                # start a new series and reset per-series state
                gd = series_match.groupdict()
                current_series_id = gd["series_id"]
                tmp_dict[current_series_id] = {
                    "series": {
                        "series_id": gd["series_id"],
                        "series_name": sanitize(gd["series_name"]),
                        "seasons_count": str(gd["seasons_count"]),
                    },
                    "seasons": {}
                }
                seasons_meta.clear()
                episodes_by_season.clear()
                flat_groups.clear()
                current_season_key = None
                skip_current_season = False
                current_flat_main_code = None
                current_group_local_index = 0
                continue

            if not current_series_id:

                # ignore noise before the first series header
                continue

            # Season (normal/special)
            season_main_match = self.season_main_pattern.match(line)
            season_special_match = self.season_special_pattern.match(line)
            season_any_special_match = self.season_any_special_pattern.match(line)

            if season_any_special_match or season_main_match or season_special_match:

                # normalize the 3 season shapes into a single set of fields
                if season_any_special_match:
                    gd = season_any_special_match.groupdict()
                    season_number = int(gd.get("season_number") or 0)
                    label_text = (gd.get("label") or "").strip()
                    season_is_special = True

                elif season_main_match:
                    gd = season_main_match.groupdict()
                    season_number = int(gd.get("season_number") or 0)
                    label_text = (gd.get("label") or "").strip()
                    season_is_special = bool(label_text and self.special_season_flag.search(label_text))

                else:
                    gd = season_special_match.groupdict()
                    season_number = int(gd.get("season_number") or 0)
                    label_text = (gd.get("label") or "").strip()
                    season_is_special = True

                season_key = f"S{season_number}"
                current_season_key = None
                skip_current_season = season_is_special

                if skip_current_season:
                    # drop special seasons like OVA, Recap, Movie
                    log_manager.debug(f"Skipping special season [{gd['season_id']}] '{label_text}' (S{season_number}).")
                    continue

                # keep normal season metadata and init episode list
                current_season_key = season_key
                seasons_meta[season_key] = {
                    "season_id": gd["season_id"],
                    "season_name": f"Season {season_number}",
                    "season_number": str(season_number),
                    "eps_count": str(int(gd["eps_count"])),
                }
                episodes_by_season.setdefault(season_key, [])
                continue

            # Episodes under current season (hierarchical section)
            if current_season_key and not skip_current_season:
                episode_match = self.episode_pattern.match(line)
                if episode_match:
                    # append raw episode rows; stream info is probed later
                    gd = episode_match.groupdict()
                    episodes_by_season[current_season_key].append(
                        (gd["episode_id"], gd["episode_title"])
                    )
                    continue

            # Flat list rows like "[S01 E03] Title"
            flat_match = self.flat_episode_pattern.match(line)
            if flat_match:
                gd = flat_match.groupdict()
                season_code_raw = int(gd['season_code'])
                download_str = gd["download_number"]

                # skip fractional entries like 7.5 which are usually recaps or extras
                if '.' in download_str:
                    log_manager.debug(f"Skipping fractional flat episode E{download_str} (treated as special).")
                    continue

                episode_download_number = int(download_str)

                # start a new flat group when season code changes
                if season_code_raw != current_flat_main_code:
                    current_flat_main_code = season_code_raw
                    flat_groups.append({"season_code": season_code_raw, "map": {}})
                    current_group_local_index = 0

                # record mapping from tree index to download index
                current_group_local_index += 1
                flat_groups[-1]["map"][current_group_local_index] = episode_download_number
                continue

        # if we never saw a series header, return an empty result
        if not current_series_id:
            log_manager.warning("No HiDive series detected in output.")

            if add2queue:
                queue_manager.add(tmp_dict, self.queue_service)

            return tmp_dict

        # enforce S1..SX order for seasons we kept
        ordered_seasons = sorted(seasons_meta.items(), key=lambda kv: int(kv[1]["season_number"]))

        # pointer into flat_groups
        flat_ptr = 0

        # total count of kept episodes across all seasons
        total_episodes = 0

        for _season_idx, (season_key, meta) in enumerate(ordered_seasons, start=1):
            season_id = meta["season_id"]
            season_number = int(meta["season_number"])
            episode_list = episodes_by_season.get(season_key, [])
            declared_count = int(meta.get("eps_count") or 0)

            # pick a flat map whose season_code matches this season number
            download_map = {}
            i = flat_ptr
            while i < len(flat_groups):
                cand = flat_groups[i]  # {"season_code": int, "map": dict}
                if cand["season_code"] == season_number:
                    download_map = cand["map"]
                    flat_ptr = i + 1
                    break
                i += 1

            # fallback: accept the next group with size close to declared count
            if not download_map:
                while flat_ptr < len(flat_groups):
                    cand = flat_groups[flat_ptr]
                    if _group_matches(len(cand["map"]), declared_count):
                        download_map = cand["map"]
                        flat_ptr += 1
                        break
                    flat_ptr += 1

            if not download_map:
                # fall back to sequential download numbering later
                log_manager.debug(f"No flat map matched for {season_key}; falling back to 1..N.")

            # produce a list of download indices in tree order
            if download_map:
                flat_order = [download_map[k] for k in sorted(download_map.keys())]
            else:
                flat_order = []

            flat_idx = 0  # consume only when we keep a hierarchical episode
            filtered_episode_rows = []

            for local_tree_index, (episode_id, title) in enumerate(episode_list, start=1):
                # drop unreleased and special episodes based on title cues
                if title and (self.special_episode_title_flag.search(title) or self.unreleased_title_flag.search(title)):
                    log_manager.debug(f"Skipping unavailable/special at {season_key} idx={local_tree_index} title='{title}'.")
                    continue

                # choose the download number from flat mapping if available
                if flat_idx < len(flat_order):
                    download_num = flat_order[flat_idx]
                    flat_idx += 1
                else:
                    # otherwise assign sequentially among kept episodes
                    download_num = flat_idx + 1
                    flat_idx += 1

                filtered_episode_rows.append((local_tree_index, episode_id, title, download_num))

            # build the final episodes dict and probe stream languages for each kept episode
            episodes_dict = {}
            for local_index, (_, _episode_id, title, download_num) in enumerate(filtered_episode_rows, start=1):
                dubs_list, subs_list = self._probe_episode_streams(series_id=current_series_id, season_id=season_id, episode_index=download_num)

                # dedupe because probes can repeat values across lines
                dubs_list = dedupe_casefold(dubs_list)
                subs_list = dedupe_casefold(subs_list)

                episode_key = f"E{local_index}"
                episodes_dict[episode_key] = {
                    "episode_number": str(local_index),
                    "episode_number_download": str(download_num),
                    "episode_name": sanitize(title) if title else f"Episode {local_index}",
                    "available_dubs": dubs_list,
                    "available_subs": subs_list,
                    "episode_downloaded": False,
                    "episode_skip": False,
                    "has_all_dubs_subs": False,
                }
                total_episodes += 1

            # attach the season to the output
            tmp_dict[current_series_id]["seasons"][season_key] = {
                "season_id": season_id,
                "season_name": sanitize(meta["season_name"]),
                "season_number": meta["season_number"],
                "episodes": episodes_dict,
                "eps_count": str(len(episodes_dict))
            }

        # apply per-series blacklist to mark episodes to skip
        tmp_dict = apply_series_blacklist(tmp_dict, config.hidive_monitor_series_id, service="hidive")

        # fill in total ep count on series metadata
        tmp_dict[current_series_id]["series"]["eps_count"] = str(total_episodes)

        log_manager.debug("Console output processed.")
        if add2queue:
            # push the parsed result to the queue for downstream consumers
            queue_manager.add(tmp_dict, self.queue_service)
        return tmp_dict

    def _probe_episode_streams(self, series_id: str, season_id: str, episode_index: int):
        """Probe available audio and subtitle streams for a specific episode."""

        log_manager.info(f"Probing streams for series {series_id} season {season_id} episode {episode_index}...")

        # "--dubLang und" returns the available dubs/subs without actually downloading the episode
        cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", str(series_id), "-s", str(season_id), "-e", str(episode_index), "--dubLang", "und"]

        log_manager.debug(f"Probing streams: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            # combine streams because MDNX sometimes prints headers on stderr
            combined_text = (result.stdout or "") + "\n" + (result.stderr or "")
            log_manager.debug(f"Probe output:\n{combined_text}")
        except Exception as exc:
            # if the probe fails we return empty lists so the caller can decide how to proceed
            log_manager.error(f"Probe failed (series {series_id} season {season_id} episode {episode_index}): {exc}")
            return [], []

        available_dubs = []  # collected normalized audio codes like "eng", "jpn"
        available_subs = []  # collected normalized subtitle locales like "en", "pt-BR"
        in_audios = False    # simple state machine to read multi-line sections
        in_subs = False

        for raw_line in combined_text.splitlines():
            line = raw_line.strip()

            if not line:
                # blank lines end any active section block
                in_audios = False
                in_subs = False
                continue

            # header like "Audio: English, Japanese"
            if self.audio_header.search(raw_line):
                in_audios, in_subs = True, False

                # parse tokens on the same header line, if present
                tail = self.audio_header.split(raw_line, 1)[-1].strip()
                if tail:
                    for token in self._clean_tokens(tail):
                        code = self._norm_audio(token)  # map display name or code to canonical audio code
                        if code:
                            available_dubs.append(code)
                continue

            # header like "Subs: EN, PT-BR"
            if self.subs_header.search(raw_line):
                in_audios, in_subs = False, True

                # parse tokens on the same header line, if present
                tail = self.subs_header.split(raw_line, 1)[-1].strip()
                if tail:
                    for token in self._clean_tokens(tail):
                        loc = self._norm_sub(token)  # map display name or code to canonical locale
                        if loc:
                            available_subs.append(loc)
                continue

            # continuation lines under the Audio section
            if in_audios and line:
                for token in self._clean_tokens(line):
                    code = self._norm_audio(token)
                    if code:
                        available_dubs.append(code)
                continue

            # continuation lines under the Subs section
            if in_subs and line:
                for token in self._clean_tokens(line):
                    loc = self._norm_sub(token)
                    if loc:
                        available_subs.append(loc)
                continue

        # remove duplicates while preserving case-insensitive uniqueness
        dubs_deduped = dedupe_casefold(available_dubs)
        subs_deduped = dedupe_casefold(available_subs)

        log_manager.info(f"Probe S{season_id}E{episode_index}: dubs={dubs_deduped}, subs={subs_deduped}")

        return dubs_deduped, subs_deduped

    def _clean_tokens(self, text: str):
        """Split a comma-separated list, trim, drop empties."""

        if not text:
            return []

        tokens = []
        for token in text.split(','):
            token = token.strip()
            if token:  # non-empty after stripping
                tokens.append(token)

        return tokens

    def _strip_parens(self, text: str):
        """Drop bracketed/parenthetical chunks."""
        return re.sub(r'\s*[\(\[\{].*?[\)\]\}]\s*', '', text or '').strip()

    def _norm_audio(self, token: str):
        """Normalize audio display name or code to canonical audio code."""

        if not token:
            return None
        lowered = self._strip_parens(token).strip().lower()

        pair = self._lang_display_to_pair.get(lowered)
        if pair:
            return (pair[0] or "").lower() or None

        if lowered in CODE_TO_LOCALE:
            return lowered

        return None

    def _norm_sub(self, token: str):
        """Normalize subtitle display name or code to canonical locale."""

        if not token:
            return None

        cleaned = self._strip_parens(token).strip()
        lowered = cleaned.lower()

        pair = self._lang_display_to_pair.get(lowered)
        if pair:
            return pair[1]

        if lowered in CODE_TO_LOCALE:
            mapped_locale = CODE_TO_LOCALE[lowered]
            for canonical in VALID_LOCALES:
                if canonical.lower() == mapped_locale.lower():
                    return canonical
            return mapped_locale

        for canonical in VALID_LOCALES:
            if canonical.lower() == lowered:
                return canonical

        return None
