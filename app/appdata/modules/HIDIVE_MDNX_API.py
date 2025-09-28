import os
import re
import sys
import subprocess

# Custom imports
from .Globals import queue_manager
from .Vars import (
    logger, config,
    VALID_LOCALES, CODE_TO_LOCALE, LANG_MAP, MDNX_SERVICE_BIN_PATH, MDNX_API_OK_LOGS,
    sanitize, dedupe_casefold
)



class HIDIVE_MDNX_API:
    def __init__(self) -> None:
        self.mdnx_path = MDNX_SERVICE_BIN_PATH
        self.mdnx_service = "hidive"
        self.queue_service = "hidive"
        self.username = str(config["app"]["HIDIVE_USERNAME"])
        self.password = str(config["app"]["HIDIVE_PASSWORD"])

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
        self.flat_episode_pattern = re.compile(r'^\[S(?P<season_code>\d{1,3})\s*E(?P<download_number>\d{1,4})\]\s+(?P<title>.+?)\s*$', re.IGNORECASE)

        # Probe headers
        self.audio_header = re.compile(r'(?i)\bAudio(?:s|(?:\s+Tracks)?)\s*:\s*')
        self.subs_header = re.compile(r'(?i)\bSub(?:s|titles?)\s*:\s*')

        # Special markers
        self.special_season_flag = re.compile(r'\b(OVA|OAD|ONA|Specials?|Recap|Compilation|Summary|Movie|Film)\b', re.IGNORECASE)
        self.special_episode_title_flag = re.compile(r'\b(recaps?|digest|compilation|summary|omake|extra|preview|prologue|specials?|ova|oad|ona)\b', re.IGNORECASE)

        # Display name -> (audio_code, subtitle_locale), e.g., "English" -> ("eng", "en")
        self._lang_display_to_pair = {name.lower(): pair for name, pair in LANG_MAP.items()}

        # stdout line-buffering if available
        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            logger.debug("[HIDIVE_MDNX_API] Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            logger.debug("[HIDIVE_MDNX_API] stdbuf not found, using default command without buffering.")

        logger.info(f"[HIDIVE_MDNX_API] MDNX API initialized with: Path: {self.mdnx_path} | Service: {self.mdnx_service}")

    def _clean_tokens(self, text: str):
        """Split a comma-separated list, trim, drop empties."""
        if not text:
            return []
        return [token.strip() for token in text.split(',') if token and token.strip()]

    def _strip_parens(self, text: str):
        """Drop bracketed/parenthetical chunks."""
        return re.sub(r'\s*[\(\[\{].*?[\)\]\}]\s*', '', text or '').strip()

    def _norm_audio(self, token: str):
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

    def process_console_output(self, output: str, add2queue: bool = True):
        logger.debug("[HIDIVE_MDNX_API] Processing console output...")
        tmp_dict = {}
        current_series_id = None
        current_season_key = None

        seasons_meta = {}
        episodes_by_season = {}

        flat_groups = []
        current_flat_main_code = None
        current_group_local_index = 0
        skip_current_season = False

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("[ERROR]") or line.startswith("[WARN]"):
                continue

            # Series
            series_match = self.series_pattern.match(line)
            if series_match:
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
                continue

            # Season (normal/special)
            season_main_match = self.season_main_pattern.match(line)
            season_special_match = self.season_special_pattern.match(line)
            season_any_special_match = self.season_any_special_pattern.match(line)

            if season_any_special_match or season_main_match or season_special_match:
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
                    logger.debug(f"[HIDIVE_MDNX_API] Skipping special season [{gd['season_id']}] '{label_text}' (S{season_number}).")
                    continue

                current_season_key = season_key
                seasons_meta[season_key] = {
                    "season_id": gd["season_id"],
                    "season_name": f"Season {season_number}",
                    "season_number": str(season_number),
                    "eps_count": str(int(gd["eps_count"])),
                }
                episodes_by_season.setdefault(season_key, [])
                continue

            # Episodes under current season
            if current_season_key and not skip_current_season:
                episode_match = self.episode_pattern.match(line)
                if episode_match:
                    gd = episode_match.groupdict()
                    episodes_by_season[current_season_key].append(
                        (gd["episode_id"], gd["episode_title"])
                    )
                    continue

            # Flat list rows
            flat_match = self.flat_episode_pattern.match(line)
            if flat_match:
                gd = flat_match.groupdict()
                season_code_raw = int(gd['season_code'])
                episode_download_number = int(gd["download_number"])

                if season_code_raw != current_flat_main_code:
                    current_flat_main_code = season_code_raw
                    flat_groups.append({})
                    current_group_local_index = 0

                current_group_local_index += 1
                flat_groups[-1][current_group_local_index] = episode_download_number
                continue

        if not current_series_id:
            logger.warning("[HIDIVE_MDNX_API] No HiDive series detected in output.")
            if add2queue:
                queue_manager.add(tmp_dict, self.queue_service)
            return tmp_dict

        total_episodes = 0
        ordered_seasons = sorted(seasons_meta.items(), key=lambda kv: int(kv[1]["season_number"]))

        # Walk flat buckets and match by size (tolerate +1/+2 for E0/noise)
        flat_ptr = 0

        def _group_matches(count_group: int, count_declared: int) -> bool:
            return (count_group == count_declared) or (count_group == count_declared + 1) or (count_group == count_declared + 2)

        for season_idx, (season_key, meta) in enumerate(ordered_seasons, start=1):
            season_id = meta["season_id"]
            episode_list = episodes_by_season.get(season_key, [])
            declared_count = int(meta.get("eps_count") or 0)

            flat_map_for_this_season = {}
            while flat_ptr < len(flat_groups):
                candidate = flat_groups[flat_ptr]
                if _group_matches(len(candidate), declared_count):
                    flat_map_for_this_season = candidate
                    flat_ptr += 1
                    break
                flat_ptr += 1

            filtered_episode_rows = []
            for local_tree_index, (episode_id, title) in enumerate(episode_list, start=1):
                download_num = flat_map_for_this_season.get(local_tree_index, local_tree_index)

                if download_num == 0:
                    logger.debug(f"[HIDIVE_MDNX_API] Skipping recap/special (E0) at {season_key} idx={local_tree_index} title='{title}'.")
                    continue
                if title and self.special_episode_title_flag.search(title):
                    logger.debug(f"[HIDIVE_MDNX_API] Skipping special-like episode by title at {season_key} idx={local_tree_index} title='{title}'.")
                    continue

                filtered_episode_rows.append((local_tree_index, episode_id, title, download_num))

            episodes_dict = {}
            for local_index, (_, episode_id, title, download_num) in enumerate(filtered_episode_rows, start=1):
                dubs_list, subs_list = self._probe_episode_streams(
                    series_id=current_series_id,
                    season_id=season_id,
                    episode_index=download_num
                )

                dubs_list = dedupe_casefold(dubs_list)
                subs_list = dedupe_casefold(subs_list)

                episode_key = f"E{local_index}"
                episodes_dict[episode_key] = {
                    "episode_number": str(local_index),
                    "episode_number_download": str(download_num),
                    "episode_name": sanitize(title) if title else f"Episode {local_index}",
                    "available_dubs": dubs_list,
                    "available_subs": subs_list,
                    "episode_downloaded": False
                }
                total_episodes += 1

            tmp_dict[current_series_id]["seasons"][season_key] = {
                "season_id": season_id,
                "season_name": sanitize(meta["season_name"]),
                "season_number": meta["season_number"],
                "episodes": episodes_dict,
                "eps_count": str(len(episodes_dict))
            }

        tmp_dict[current_series_id]["series"]["eps_count"] = str(total_episodes)

        logger.debug("[HIDIVE_MDNX_API] Console output processed.")
        if add2queue:
            queue_manager.add(tmp_dict, self.queue_service)
        return tmp_dict

    def _probe_episode_streams(self, series_id: str, season_id: str, episode_index: int):
        logger.info(f"[HIDIVE_MDNX_API] Probing streams for series {series_id} season {season_id} episode {episode_index}...")

        cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", str(series_id), "-s", str(season_id), "-e", str(episode_index), "--dubLang", "und"]

        logger.debug(f"[HIDIVE_MDNX_API] Probing streams: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            combined_text = (result.stdout or "") + "\n" + (result.stderr or "")
            logger.debug(f"[HIDIVE_MDNX_API] Probe output:\n{combined_text}")
        except Exception as exc:
            logger.error(f"[HIDIVE_MDNX_API] Probe failed (series {series_id} season {season_id} episode {episode_index}): {exc}")
            return [], []

        available_dubs = []
        available_subs = []
        in_audios = False
        in_subs = False

        for raw_line in combined_text.splitlines():
            line = raw_line.strip()
            if not line:
                in_audios = False
                in_subs = False
                continue

            if self.audio_header.search(raw_line):
                in_audios, in_subs = True, False
                tail = self.audio_header.split(raw_line, 1)[-1].strip()
                if tail:
                    for token in self._clean_tokens(tail):
                        code = self._norm_audio(token)
                        if code:
                            available_dubs.append(code)
                continue

            if self.subs_header.search(raw_line):
                in_audios, in_subs = False, True
                tail = self.subs_header.split(raw_line, 1)[-1].strip()
                if tail:
                    for token in self._clean_tokens(tail):
                        loc = self._norm_sub(token)
                        if loc:
                            available_subs.append(loc)
                continue

            if in_audios and line:
                for token in self._clean_tokens(line):
                    code = self._norm_audio(token)
                    if code:
                        available_dubs.append(code)
                continue

            if in_subs and line:
                for token in self._clean_tokens(line):
                    loc = self._norm_sub(token)
                    if loc:
                        available_subs.append(loc)
                continue

        dubs_deduped = dedupe_casefold(available_dubs)
        subs_deduped = dedupe_casefold(available_subs)

        logger.info(f"[HIDIVE_MDNX_API] Probe S{season_id}E{episode_index}: dubs={dubs_deduped}, subs={subs_deduped}")

        return dubs_deduped, subs_deduped

    def test(self) -> None:
        logger.info("[HIDIVE_MDNX_API] Testing MDNX API...")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", "1244"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8").stdout
        logger.debug(f"[HIDIVE_MDNX_API] MDNX API test result:\n{result}")

        json_result = self.process_console_output(result, add2queue=False)
        logger.info(f"[HIDIVE_MDNX_API] Processed console output:\n{json_result}")

        ### This needs to be researched/tested more. I am not sure what anidl outputs on auth errors with HiDive.
        ### Leaving commented out for now. This means there will be no auto re-auth on auth errors for HiDive.
        # Check if the output contains authentication errors
        # error_triggers = ["invalid_grant", "Token Refresh Failed", "Authentication required", "Anonymous"]
        # if any(trigger in result for trigger in error_triggers):
        #     logger.info("[HIDIVE_MDNX_API] Authentication error detected. Forcing re-authentication...")
        #     self.auth()
        # else:
        #     logger.info("[HIDIVE_MDNX_API] MDNX API test successful.")

        logger.info("[HIDIVE_MDNX_API] MDNX API test successful.")
        return

    def auth(self) -> str:
        logger.info(f"[HIDIVE_MDNX_API] Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            logger.error("[HIDIVE_MDNX_API] MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nHIDIVE_USERNAME\nHIDIVE_PASSWORD\nExiting...")
            sys.exit(1)

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--auth", "--username", self.username, "--password", self.password, "--silentAuth"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.info(f"[HIDIVE_MDNX_API] Console output for auth process:\n{result.stdout}")

        logger.info(f"[HIDIVE_MDNX_API] Authentication with {self.mdnx_service} complete.")
        return result.stdout

    def start_monitor(self, series_id: str) -> str:
        logger.info(f"[HIDIVE_MDNX_API] Monitoring series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.debug(f"[HIDIVE_MDNX_API] Console output for start_monitor process:\n{result.stdout}")

        self.process_console_output(result.stdout)

        logger.debug(f"[HIDIVE_MDNX_API] Monitoring for series with ID: {series_id} complete.")
        return result.stdout

    def stop_monitor(self, series_id: str) -> None:
        queue_manager.remove(series_id, self.queue_service)
        logger.info(f"[HIDIVE_MDNX_API] Stopped monitoring series with ID: {series_id}")
        return

    def update_monitor(self, series_id: str) -> str:
        logger.info(f"[HIDIVE_MDNX_API] Updating monitor for series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.debug(f"[HIDIVE_MDNX_API] Console output for update_monitor process:\n{result.stdout}")

        self.process_console_output(result.stdout)

        logger.debug(f"[HIDIVE_MDNX_API] Updating monitor for series with ID: {series_id} complete.")
        return result.stdout

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list = None) -> bool:
        logger.info(f"[HIDIVE_MDNX_API] Downloading episode {episode_number} for series {series_id} season {season_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id, "-s", season_id, "-e", episode_number]

        if dub_override is False:
            logger.info("[HIDIVE_MDNX_API] No dubs were found for this episode, skipping download.")
            return False

        if dub_override:
            tmp_cmd += ["--dubLang", *dub_override]
            logger.info(f"[HIDIVE_MDNX_API] Using dubLang override: {' '.join(dub_override)}")

        # Hardcoded options.
        # These can not be modified by config.json, or things will break/not work as expected.
        tmp_cmd += ["--fileName", "output"]
        tmp_cmd += ["--skipUpdate", "true"]

        if self.stdbuf_exists:
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            cmd = tmp_cmd

        logger.info(f"[HIDIVE_MDNX_API] Executing command: {' '.join(cmd)}")

        success = False
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                cleaned = line.rstrip()
                logger.info(f"[HIDIVE_MDNX_API][multi-downloader-nx] {cleaned}")
                if any(ok_log in cleaned for ok_log in MDNX_API_OK_LOGS):
                    success = True

        if proc.returncode != 0:
            logger.error(f"[HIDIVE_MDNX_API] Download failed with exit code {proc.returncode}")
            return False

        if not success:
            logger.error("[HIDIVE_MDNX_API] Download did not report successful download. Assuming failure.")
            return False

        logger.info("[HIDIVE_MDNX_API] Download finished successfully.")
        return True
