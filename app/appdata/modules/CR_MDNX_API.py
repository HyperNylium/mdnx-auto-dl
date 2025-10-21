import os
import re
import sys
import subprocess

# Custom imports
from .Globals import queue_manager
from .Vars import (
    logger, config,
    VALID_LOCALES, NAME_TO_CODE, MDNX_SERVICE_BIN_PATH, MDNX_API_OK_LOGS,
    sanitize
)


class CR_MDNX_API:
    def __init__(self) -> None:
        self.mdnx_path = MDNX_SERVICE_BIN_PATH
        self.mdnx_service = "crunchy"
        self.queue_service = "crunchy"
        self.username = str(config["app"]["CR_USERNAME"])
        self.password = str(config["app"]["CR_PASSWORD"])

        # Series: lines starting with [Z...]
        self.series_pattern = re.compile(
            r'^\[Z:(?P<series_id>\w+)\]\s+(?P<series_name>.+?)\s+\(Seasons:\s*(?P<seasons_count>\d+),\s*EPs:\s*(?P<eps_count>\d+)\)'
        )

        # Seasons: lines starting with [S...]
        self.season_pattern = re.compile(
            r'^\[S:(?P<season_id>\w+)\]\s+(?P<season_name>.+?)\s+\(Season:\s*(?P<season_number>\d+)\)'
        )

        # Episodes: lines starting with [E...] or [S...]
        self.episode_pattern = re.compile(
            r'^\[(?P<ep_type>E|S)(?P<episode_number>\d+)\]\s+(?P<full_episode_name>.+)$'
        )

        # Versions (dubs): lines starting with "- Versions":
        self.versions_pattern = re.compile(
            r'-\s*Versions:\s*(.+)'
        )

        # Subtitles: lines starting with "- Subtitles":
        self.subtitles_pattern = re.compile(
            r'-\s*Subtitles:\s*(.+)'
        )

        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            logger.debug("[CR_MDNX_API] Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            logger.debug("[CR_MDNX_API] stdbuf not found, using default command without buffering.")

        # Skip API test if user wants to
        if config["app"]["CR_SKIP_API_TEST"] == False:
            self.test()
        else:
            logger.info("[CR_MDNX_API] API test skipped by user.")

        logger.info(f"[CR_MDNX_API] MDNX API initialized with: Path: {self.mdnx_path} | Service: {self.mdnx_service}")

    def process_console_output(self, output: str, add2queue: bool = True):
        logger.debug("[CR_MDNX_API] Processing console output...")
        tmp_dict = {}             # maps series_id to series info
        episode_counters = {}     # maps season key ("S1", "S2", etc) to episode counter
        season_num_map = {}       # we keep the first numeric label we see as a hint for fallback resolution
        season_id_to_key = {}     # we map season_id to "S{n}" in order of appearance to avoid duplicate label collisions
        season_order = 0          # running index of seasons as they appear
        current_series_id = None
        active_season_key = None
        active_episode_key = None  # holds the current episode key like "E1"
        name_to_season_key = {}   # map normalized season_name to season_key so episodes can resolve by name first

        # we stage an episode because its dubs/subs lines arrive after the [E..] line
        staged_episode = None  # dict with: series_id, season_key, ep_key, episode_number_clean, episode_number_download, episode_title_clean, available_subs, available_dubs

        def _commit_staged():
            # we need to flush the staged episode into tmp_dict when context changes or at the end
            nonlocal staged_episode
            if not staged_episode:
                return
            s_id = staged_episode["series_id"]
            s_key = staged_episode["season_key"]
            e_key = staged_episode["ep_key"]

            # create a shell season if an episode appeared before its header
            if s_key not in tmp_dict[s_id]["seasons"]:
                tmp_dict[s_id]["seasons"][s_key] = {
                    "season_id": None,
                    "season_name": None,
                    "season_number": tmp_dict[s_id]["seasons"].get(s_key, {}).get("season_number", s_key[1:]),
                    "episodes": {}
                }

            # write the staged episode
            tmp_dict[s_id]["seasons"][s_key]["episodes"][e_key] = {
                "episode_number": staged_episode["episode_number_clean"],
                "episode_number_download": staged_episode["episode_number_download"],
                "episode_name": staged_episode["episode_title_clean"],
                "available_dubs": staged_episode["available_dubs"],
                "available_subs": staged_episode["available_subs"],
                "episode_downloaded": False,
                "episode_skip": False
            }

            logger.debug(f"[CR_MDNX_API] Committed episode {s_id}/{s_key}/{e_key} to tmp_dict.")
            staged_episode = None
            return

        for raw_line in output.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            # series header like "[Z:...] <name> (Seasons: X, EPs: Y)"
            match = self.series_pattern.match(line)
            if match:
                # we commit any staged episode before switching series
                _commit_staged()

                info = match.groupdict()

                # sanitize because series_name may be used in filesystem paths
                info["series_name"] = sanitize(info["series_name"])

                # reset per-series state
                current_series_id = info["series_id"]
                tmp_dict[current_series_id] = {"series": info, "seasons": {}}
                season_num_map.clear()
                season_id_to_key.clear()
                season_order = 0
                episode_counters.clear()
                active_season_key = None
                active_episode_key = None
                name_to_season_key.clear()
                continue

            # season header like "[S:...] <name> (Season: N)"
            match = self.season_pattern.match(line)
            if match and current_series_id:
                # we commit any staged episode before changing season context
                _commit_staged()

                info = match.groupdict()
                info["season_name"] = sanitize(info["season_name"])

                # we key seasons by season_id and appearance order so duplicate "Season: 1" labels do not collide
                season_id = info["season_id"]
                if season_id not in season_id_to_key:
                    season_order += 1
                    mapped_num = season_order
                    season_id_to_key[season_id] = f"S{mapped_num}"
                    # we remember the first numeric label as a hint for later numeric fallback
                    try:
                        orig_num = int(info["season_number"])
                        season_num_map.setdefault(orig_num, mapped_num)
                    except Exception:
                        pass

                season_key = season_id_to_key[season_id]
                mapped_num = int(season_key[1:])
                active_season_key = season_key
                active_episode_key = None
                info["season_number"] = str(mapped_num)

                # create the season bucket
                tmp_dict[current_series_id]["seasons"][season_key] = {
                    **info,
                    "episodes": {}
                }
                episode_counters[season_key] = 1

                # we memo the name to resolve episodes by name first
                name_to_season_key[sanitize(info["season_name"]).lower()] = season_key
                continue

            # episode line like "[E12] [YYYY-MM-DD] <Series Name> - Season N - Episode M"
            match = self.episode_pattern.match(line)
            if match and current_series_id:
                # we commit any previous staged episode before staging a new one
                _commit_staged()

                ep_info = match.groupdict()

                # skip specials like "[Sxx]" because we index only normal episodes
                if ep_info["ep_type"] == "S":
                    continue

                # skip PV or trailer entries that are not full episodes
                if ep_info["full_episode_name"].lstrip().lower().startswith("pv"):
                    continue

                # resolve which mapped season this episode belongs to
                season_key = None
                mapped_num = None

                # we extract the display name portion before " - Season "
                full_name_guess = ep_info["full_episode_name"]
                full_name_guess = re.sub(r'^\[\d{4}-\d{2}-\d{2}\]\s*', '', full_name_guess)  # strip leading date if present
                parts_before = full_name_guess.split(' - Season ', 1)
                season_name_guess = parts_before[0].strip()

                # try by season name first because names disambiguate duplicate numeric labels
                guessed_key = name_to_season_key.get(sanitize(season_name_guess).lower())
                if guessed_key:
                    season_key = guessed_key
                    mapped_num = int(season_key[1:])
                    logger.debug(f"[CR_MDNX_API] Resolved episode season by name '{season_name_guess}' -> {season_key}")

                # fallback to the numeric label found in the episode line if name lookup failed
                if not season_key:
                    season_num = re.search(r'- Season (\d+) -', line)
                    if season_num:
                        orig_label = int(season_num.group(1))
                        if orig_label in season_num_map:
                            mapped_num = season_num_map[orig_label]
                            season_key = f"S{mapped_num}"

                if not season_key:
                    # if we still cannot resolve, we create a shell season so the episode is not lost
                    logger.warning(f"[CR_MDNX_API] Season not resolved by number or name in line: {line}")
                    mapped_num = len(tmp_dict[current_series_id]["seasons"]) + 1
                    season_key = f"S{mapped_num}"
                    if season_key not in tmp_dict[current_series_id]["seasons"]:
                        tmp_dict[current_series_id]["seasons"][season_key] = {
                            "season_id": None,
                            "season_name": None,
                            "season_number": str(mapped_num),
                            "episodes": {}
                        }
                        episode_counters[season_key] = 1

                    # we stabilize future matches by updating maps from what we can infer here
                    season_num = re.search(r'- Season (\d+) -', line)
                    if season_num:
                        orig_label = int(season_num.group(1))
                        season_num_map.setdefault(orig_label, mapped_num)
                    name_to_season_key[sanitize(season_name_guess).lower()] = season_key

                # make sure the per-season counter exists even if there was no header
                if season_key not in episode_counters:
                    episode_counters[season_key] = 1

                # assign contiguous episode index inside the mapped season
                idx = episode_counters[season_key]
                ep_key = f"E{idx}"
                episode_number_clean = str(idx)
                episode_counters[season_key] += 1
                episode_number_download = episode_number_clean  # we keep download numbering aligned with clean numbering

                # extract a clean episode title from the tail after the last " - "
                parts = ep_info["full_episode_name"].rsplit(" - ", 1)
                if len(parts) > 1:
                    episode_title_clean = parts[-1]
                else:
                    episode_title_clean = ep_info["full_episode_name"]
                episode_title_clean = sanitize(episode_title_clean)

                # stage the episode so we can attach dubs and subs from following lines
                active_season_key = season_key
                active_episode_key = ep_key
                staged_episode = {
                    "series_id": current_series_id,
                    "season_key": season_key,
                    "ep_key": ep_key,
                    "episode_number_clean": episode_number_clean,
                    "episode_number_download": episode_number_download,
                    "episode_title_clean": episode_title_clean,
                    "available_dubs": [],
                    "available_subs": []
                }
                logger.debug(f"[CR_MDNX_API] Staged new episode {current_series_id}/{season_key}/{ep_key}: '{episode_title_clean}'")
                continue

            # versions line like "- Versions: en, es-419, ..."
            match = self.versions_pattern.match(line)
            if match and current_series_id and active_season_key and active_episode_key and staged_episode and staged_episode.get("ep_key") == active_episode_key:
                raw_list = match.group(1)

                # we normalize entries and map human readable names to language codes
                dub_codes = []
                for lang in raw_list.split(','):
                    lang = lang.strip().lstrip('☆').strip()  # strip the star marker the tool uses to indicate premium dubs
                    if lang in NAME_TO_CODE:
                        dub_codes.append(NAME_TO_CODE[lang])

                staged_episode["available_dubs"] = dub_codes
                logger.debug(f"[CR_MDNX_API] Staged episode-level dubs for {current_series_id}/{active_season_key}/{active_episode_key}: {dub_codes}")
                continue

            # subtitles line like "- Subtitles: en-US, es-ES, ..."
            match = self.subtitles_pattern.match(line)
            if match and current_series_id and active_season_key and active_episode_key and staged_episode and staged_episode.get("ep_key") == active_episode_key:
                raw_list = match.group(1).strip()

                subs_locales = []
                if raw_list.lower() != "none":
                    for raw_locale in raw_list.split(','):
                        token = raw_locale.strip()
                        if token in VALID_LOCALES:
                            subs_locales.append(token)
                            continue
                        # fallback to base language if regioned code is not in VALID_LOCALES
                        base = token.split('-', 1)[0]
                        if base in VALID_LOCALES:
                            subs_locales.append(base)

                staged_episode["available_subs"] = subs_locales
                logger.debug(f"[CR_MDNX_API] Staged episode-level subtitles for {current_series_id}/{active_season_key}/{active_episode_key}: {subs_locales}")
                continue

        # commit any trailing staged episode once the loop ends
        _commit_staged()

        # apply per-series blacklist to mark episodes to skip
        cr_cfg = config.get("cr_monitor_series_id", {})
        if not isinstance(cr_cfg, dict):
            logger.error("[CR_MDNX_API] cr_monitor_series_id must be a dict in config.")
            cr_cfg = {}

        # rules are strings like "S:<season_id>" or "S:<season_id>:E:<index>"
        def _parse_rules(rules):
            seasons = set()
            eps = {}
            if not rules:
                return seasons, eps
            if isinstance(rules, str):
                # empty string means no blacklist
                if not rules.strip():
                    return seasons, eps
                rules = [rules]
            for raw in rules:
                if not raw:
                    continue
                s = str(raw).strip()
                m = re.fullmatch(r"S:([^:]+)(?::E:(\d+))?", s)
                if not m:
                    continue
                sid, epi = m.group(1), m.group(2)
                if epi is None:
                    seasons.add(sid)
                else:
                    eps.setdefault(sid, set()).add(int(epi))
            return seasons, eps

        for sid, s_info in tmp_dict.items():
            rules = cr_cfg.get(sid)
            if rules is None:
                continue
            bl_seasons, bl_eps = _parse_rules(rules)
            if not bl_seasons and not bl_eps:
                continue

            for _season_key, season_info in (s_info.get("seasons") or {}).items():
                season_id = season_info.get("season_id")
                if not season_id:
                    continue

                # season-level blacklist
                if season_id in bl_seasons:
                    for ep in (season_info.get("episodes") or {}).values():
                        ep["episode_skip"] = True
                    continue

                # episode-level blacklist for this season_id
                idx_set = bl_eps.get(season_id)
                if idx_set:
                    for ep_key, ep in (season_info.get("episodes") or {}).items():
                        try:
                            idx = int(str(ep_key).lstrip("E"))
                            if idx in idx_set:
                                ep["episode_skip"] = True
                        except Exception:
                            pass

        # we remove empty seasons and renumber contiguous S1..SX to keep structure compact
        for series_id, series_info in tmp_dict.items():
            seasons = series_info["seasons"]

            kept_seasons = []
            for key, val in seasons.items():
                if val["episodes"]:
                    kept_seasons.append((key, val))

            # sort seasons by their current mapped number so renumbering is stable
            kept_seasons.sort(key=lambda item: int(item[1]["season_number"]))

            new_seasons = {}
            new_idx = 1
            for old_key, season_info in kept_seasons:
                new_key = f"S{new_idx}"
                if new_key != old_key:
                    logger.debug(f"[CR_MDNX_API] Renaming season {old_key} to {new_key} in series {series_id}")
                season_info["season_number"] = str(new_idx)
                season_info["eps_count"] = str(len(season_info["episodes"]))
                new_seasons[new_key] = season_info
                new_idx += 1

            series_info["seasons"] = new_seasons

        logger.debug("[CR_MDNX_API] Console output processed.")
        if add2queue:
            queue_manager.add(tmp_dict, self.queue_service)
        return tmp_dict

    def test(self) -> None:
        logger.info("[CR_MDNX_API] Testing MDNX API...")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", "G8DHV78ZM"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8").stdout
        logger.info(f"[CR_MDNX_API] MDNX API test result:\n{result}")

        json_result = self.process_console_output(result, add2queue=False)
        logger.info(f"[CR_MDNX_API] Processed console output:\n{json_result}")

        # Check if the output contains authentication errors
        error_triggers = ["invalid_grant", "Token Refresh Failed", "Authentication required", "Anonymous"]
        if any(trigger in result for trigger in error_triggers):
            logger.info("[CR_MDNX_API] Authentication error detected. Forcing re-authentication...")
            self.auth()
        else:
            logger.info("[CR_MDNX_API] MDNX API test successful.")

        return

    def auth(self) -> str:
        logger.info(f"[CR_MDNX_API] Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            logger.error("[CR_MDNX_API] MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nCR_USERNAME\nCR_PASSWORD\nExiting...")
            sys.exit(1)

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--auth", "--username", self.username, "--password", self.password, "--silentAuth"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.info(f"[CR_MDNX_API] Console output for auth process:\n{result.stdout}")

        logger.info(f"[CR_MDNX_API] Authentication with {self.mdnx_service} complete.")
        return result.stdout

    def start_monitor(self, series_id: str) -> str:
        logger.info(f"[CR_MDNX_API] Monitoring series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.debug(f"[CR_MDNX_API] Console output for start_monitor process:\n{result.stdout}")

        self.process_console_output(result.stdout)

        logger.debug(f"[CR_MDNX_API] Monitoring for series with ID: {series_id} complete.")
        return result.stdout

    def stop_monitor(self, series_id: str) -> None:
        queue_manager.remove(series_id, self.queue_service)
        logger.info(f"[CR_MDNX_API] Stopped monitoring series with ID: {series_id}")
        return

    def update_monitor(self, series_id: str) -> str:
        logger.info(f"[CR_MDNX_API] Updating monitor for series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.debug(f"[CR_MDNX_API] Console output for update_monitor process:\n{result.stdout}")

        self.process_console_output(result.stdout)

        logger.debug(f"[CR_MDNX_API] Updating monitor for series with ID: {series_id} complete.")
        return result.stdout

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list | None = None) -> bool:
        logger.info(f"[CR_MDNX_API] Downloading episode {episode_number} for series {series_id} season {season_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id, "-s", season_id, "-e", episode_number]

        if dub_override is False:
            logger.info("[CR_MDNX_API] No dubs were found for this episode, skipping download.")
            return False

        if dub_override:
            tmp_cmd += ["--dubLang", *dub_override]
            logger.info(f"[CR_MDNX_API] Using dubLang override: {' '.join(dub_override)}")

        # Hardcoded options.
        # These can not be modified by config.json, or things will break/not work as expected.
        tmp_cmd += ["--fileName", "output"]
        tmp_cmd += ["--skipUpdate", "true"]

        if self.stdbuf_exists:
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            cmd = tmp_cmd

        logger.info(f"[CR_MDNX_API] Executing command: {' '.join(cmd)}")

        success = False
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                cleaned = line.rstrip()
                logger.info(f"[CR_MDNX_API][multi-downloader-nx] {cleaned}")

                if any(ok_log.lower() in cleaned.lower() for ok_log in MDNX_API_OK_LOGS):
                    success = True

        if proc.returncode != 0:
            logger.error(f"[CR_MDNX_API] Download failed with exit code {proc.returncode}")
            return False

        if not success:
            logger.error("[CR_MDNX_API] Download did not report successful download. Assuming failure.")
            return False

        logger.info("[CR_MDNX_API] Download finished successfully.")
        return True
