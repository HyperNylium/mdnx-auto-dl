import os
import re
import sys
import subprocess

# Custom imports
from .QueueManager import QueueManager
from .Vars import logger, config
from .Vars import VALID_LOCALES, NAME_TO_CODE
from .Vars import sanitize



class MDNX_API:
    def __init__(self, mdnx_path, config=config, mdnx_service="crunchy") -> None:
        self.mdnx_path = mdnx_path
        self.mdnx_service = mdnx_service
        self.username = str(config["app"]["CR_USERNAME"])
        self.password = str(config["app"]["CR_PASSWORD"])
        self.queue_manager = QueueManager()

        # Series: lines starting with [Z...]
        self.series_pattern = re.compile(
            r'^\[Z:(?P<series_id>\w+)\]\s+(?P<series_name>.+?)\s+\(Seasons:\s*(?P<seasons_count>\d+),\s*EPs:\s*(?P<eps_count>\d+)\)'
        )

        # Seasons: lines starting with [S...]
        self.season_pattern = re.compile(
            r'^\[S:(?P<season_id>\w+)\]\s+(?P<season_name>.+?)\s+\(Season:\s*(?P<season_number>\d+)\)'
        )

        # Episodes: lines starting with [E...] or [S...] (without the colon after S)
        self.episode_pattern = re.compile(
            r'^\[(?P<ep_type>E|S)(?P<episode_number>\d+)\]\s+(?P<full_episode_name>.+?)\s+\['
        )

        # Subtitles: lines starting with - Subtitles:
        self.subtitles_pattern = re.compile(
            r'-\s*Subtitles:\s*(.+)'
        )

        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            logger.debug("[MDNX_API] Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            logger.debug("[MDNX_API] stdbuf not found, using default command without buffering.")

        logger.info(f"[MDNX_API] MDNX API initialized with: Path: {mdnx_path} | Service: {mdnx_service}")

        # Skip API test if user wants to
        if config["app"]["CR_SKIP_API_TEST"] == False:
            self.test()
        else:
            logger.info("[MDNX_API] API test skipped by user.")

        # Set --tsd param if user wants to
        self.REMOVE_ALL_ACTIVE_STREAMS = False
        if config["app"]["REMOVE_ALL_ACTIVE_STREAMS"] == True:
            self.REMOVE_ALL_ACTIVE_STREAMS = True
            logger.info("[MDNX_API] User requested to remove all active streams when downloading. Setting --tsd parameter to true.")

    def process_console_output(self, output: str, add2queue: bool = True):
        logger.debug("[MDNX_API] Processing console output...")
        tmp_dict = {}
        episode_counters = {} # maps season key ("S1", "S2", etc) to episode counter
        season_num_map = {}
        season_subs = {} # maps (series_id, season_key) to list of subtitles
        current_series_id = None
        active_season_key = None

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check for series information.
            match = self.series_pattern.match(line)
            if match:
                info = match.groupdict()

                # sanitise illegal path characters
                info["series_name"] = sanitize(info["series_name"])

                current_series_id = info["series_id"]
                tmp_dict[current_series_id] = {"series": info, "seasons": {}}
                season_num_map.clear()
                episode_counters.clear()
                active_season_key = None
                continue

            # Check for season information.
            match = self.season_pattern.match(line)
            if match and current_series_id:
                info = match.groupdict()
                info["season_name"] = sanitize(info["season_name"])

                # turn Crunchyrolls season number into our own
                # so we dont get S02E13. We would get S02E01.
                orig_num = int(info["season_number"])
                if orig_num not in season_num_map:
                    season_num_map[orig_num] = len(season_num_map) + 1
                mapped_num = season_num_map[orig_num]

                season_key = f"S{mapped_num}"
                active_season_key = season_key
                info["season_number"] = str(mapped_num)

                tmp_dict[current_series_id]["seasons"][season_key] = {
                    **info,
                    "episodes": {}
                }
                episode_counters[season_key] = 1
                continue

            # Check for subtitles line.
            match = self.subtitles_pattern.match(line)
            if match and current_series_id:
                # If we are inside a season, store its subtitle list
                if active_season_key:
                    subs_locales = []
                    for raw_locale in match.group(1).split(','):
                        locale = raw_locale.strip()
                        if locale in VALID_LOCALES:
                            subs_locales.append(locale)
                    season_subs[(current_series_id, active_season_key)] = subs_locales
                # If we are at series level, ignore the list.
                # Do not want to store series subtitles, as they are not used.
                continue

            # Check for episode information.
            match = self.episode_pattern.match(line)
            if match and current_series_id:
                ep_info = match.groupdict()

                # skip special episodes (This would include OVAs, "Ex-" episodes, movies (maybe), etc.)
                if ep_info["ep_type"] == "S":
                    continue

                # skip PV / trailer episodes
                if ep_info["full_episode_name"].lstrip().lower().startswith("pv"):
                    continue

                # find season number in full line
                season_num = re.search(r'- Season (\d+) -', line)
                if not season_num:
                    logger.warning(f"[MDNX_API] Season not found in line: {line}")
                    continue
                orig_label = int(season_num.group(1))
                if orig_label not in season_num_map:
                    season_num_map[orig_label] = len(season_num_map) + 1
                mapped_num = season_num_map[orig_label]
                season_key = f"S{mapped_num}"

                # season line was missing, so create an empty season entry
                if season_key not in tmp_dict[current_series_id]["seasons"]:
                    tmp_dict[current_series_id]["seasons"][season_key] = {
                        "season_id": None,
                        "season_name": None,
                        "season_number": str(mapped_num),
                        "episodes": {}
                    }
                    episode_counters[season_key] = 1

                # extract dubs that CR can provide for this episode
                dubs_match = re.search(r'\[([^\]]+)\]\s*$', line)
                dub_codes = []
                if dubs_match:
                    for lang in dubs_match.group(1).split(','):
                        lang = lang.strip().lstrip('☆').strip()
                        if lang in NAME_TO_CODE:
                            dub_codes.append(NAME_TO_CODE[lang])

                # get subtitle list for this season
                subs_locales = season_subs.get((current_series_id, season_key), [])

                # assign contiguous episode index inside the mapped season
                idx = episode_counters[season_key]
                ep_key = f"E{idx}"
                episode_number_clean = str(idx)
                episode_counters[season_key] += 1
                episode_number_download = episode_number_clean

                parts = ep_info["full_episode_name"].rsplit(" - ", 1)
                if len(parts) > 1:
                    episode_title_clean = parts[-1]
                else:
                    episode_title_clean = ep_info["full_episode_name"]
                episode_title_clean = sanitize(episode_title_clean)

                tmp_dict[current_series_id]["seasons"][season_key]["episodes"][ep_key] = {
                    "episode_number": episode_number_clean,
                    "episode_number_download": episode_number_download,
                    "episode_name": episode_title_clean,
                    "available_dubs": dub_codes,
                    "available_subs": subs_locales,
                    "episode_downloaded": False
                }
                continue

        # Remove seasons that ended up empty and reorder them.
        # So, if there were 3 seasons, but only S1 and S3 had episodes,
        # we would end up with S1 and S2, not S1 and S3.
        for series_id, series_info in tmp_dict.items():
            seasons = series_info["seasons"]

            kept_seasons = []
            for key, val in seasons.items():
                if val["episodes"]: # keep seasons that have at least one episode
                    kept_seasons.append((key, val))

            # sort kept_seasons by the original season_number (as integers)
            kept_seasons.sort(key=lambda item: int(item[1]["season_number"]))

            new_seasons = {}
            new_idx = 1
            for old_key, season_info in kept_seasons:
                new_key = f"S{new_idx}"
                if new_key != old_key:
                    logger.info(f"[MDNX_API] Renaming season {old_key} to {new_key} in series {series_id}")
                season_info["season_number"] = str(new_idx)
                season_info["eps_count"] = str(len(season_info["episodes"]))
                new_seasons[new_key] = season_info
                new_idx += 1

            series_info["seasons"] = new_seasons

        logger.debug("[MDNX_API] Console output processed.")
        if add2queue:
            self.queue_manager.add(tmp_dict)
        return tmp_dict

    def test(self) -> None:
        logger.info("[MDNX_API] Testing MDNX API...")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", "GMEHME81V"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8").stdout
        logger.info(f"[MDNX_API] MDNX API test resault:\n{result}")
        json_result = self.process_console_output(result, add2queue=False)
        logger.info(f"[MDNX_API] Processed console output:\n{json_result}")

        # Check if the output contains authentication errors
        error_triggers = ["invalid_grant", "Token Refresh Failed", "Authentication required", "Anonymous"]
        if any(trigger in result for trigger in error_triggers):
            logger.info("[MDNX_API] Authentication error detected. Forcing re-authentication...")
            self.auth()
        else:
            logger.info("[MDNX_API] MDNX API test successful.")

        return

    def auth(self) -> str:
        logger.info(f"[MDNX_API] Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            logger.error("[MDNX_API] MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nCR_USERNAME\nCR_PASSWORD\nExiting...")
            sys.exit(1)

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--auth", "--username", self.username, "--password", self.password, "--silentAuth"]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")
        logger.info(f"[MDNX_API] Console output for auth process:\n{result.stdout}")

        logger.info(f"[MDNX_API] Authentication with {self.mdnx_service} complete.")
        return result.stdout

    def start_monitor(self, series_id: str) -> str:
        logger.info(f"[MDNX_API] Monitoring series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")

        self.process_console_output(result.stdout)

        logger.info(f"[MDNX_API] Monitoring for series with ID: {series_id} complete.")
        return result.stdout

    def stop_monitor(self, series_id: str) -> None:
        logger.info(f"[MDNX_API] Stopping monitor for series with ID: {series_id}")

        self.queue_manager.remove(series_id)

        logger.info(f"[MDNX_API] Stopping monitor for series with ID: {series_id} complete.")
        return

    def update_monitor(self, series_id: str) -> str:
        logger.info(f"[MDNX_API] Updating monitor for series with ID: {series_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id]
        result = subprocess.run(tmp_cmd, capture_output=True, text=True, encoding="utf-8")

        self.process_console_output(result.stdout)

        logger.info(f"[MDNX_API] Updating monitor for series with ID: {series_id} complete.")
        return result.stdout

    def download_episode(self, series_id: str, season_id: str, episode_number: str, dub_override: list = None) -> bool:
        logger.info(f"[MDNX_API] Downloading episode {episode_number} for series {series_id} season {season_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id, "-s", season_id, "-e", episode_number]

        if dub_override is False:
            logger.info("[MDNX_API] No dubs were found for this episode, skipping download.")
            return False

        if dub_override:
            tmp_cmd += ["--dubLang", *dub_override]
            logger.info(f"[MDNX_API] Using dubLang override: {' '.join(dub_override)}")

        if self.REMOVE_ALL_ACTIVE_STREAMS:
            tmp_cmd += ["--tsd", "true"]

        if self.stdbuf_exists:
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            cmd = tmp_cmd

        logger.info(f"[MDNX_API] Executing command: {' '.join(cmd)}")

        success = False
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                cleaned = line.rstrip()
                logger.info(f"[MDNX_API][multi-download-nx] {cleaned}")

                if "[mkvmerge Done]" in cleaned:
                    success = True

        if proc.returncode != 0:
            logger.error(f"[MDNX_API] Download failed with exit code {proc.returncode}")
            return False

        if not success:
            logger.error("[MDNX_API] Download did not report successful download. Assuming failure.")
            return False

        logger.info("[MDNX_API] Download finished successfully.")
        return True