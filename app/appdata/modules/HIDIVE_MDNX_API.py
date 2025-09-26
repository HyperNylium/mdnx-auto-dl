import os
import re
import sys
import subprocess

# Custom imports
from .Globals import queue_manager
from .Vars import (
    logger, config,
    VALID_LOCALES, NAME_TO_CODE, CODE_TO_LOCALE, LANG_MAP, MDNX_SERVICE_BIN_PATH,
    sanitize
)



class HIDIVE_MDNX_API:
    def __init__(self, mdnx_path=MDNX_SERVICE_BIN_PATH, config=config, mdnx_service="hidive") -> None:
        self.mdnx_path = mdnx_path
        self.mdnx_service = mdnx_service
        self.queue_service = "hidive"
        self.username = str(config["app"]["HIDIVE_USERNAME"])
        self.password = str(config["app"]["HIDIVE_PASSWORD"])

        # Series: lines starting with [Z.<series_id>]
        self.series_pattern = re.compile(
            r'^\[Z\.(?P<series_id>\d+)\]\s+(?P<series_name>.+?)\s+\((?P<seasons_count>\d+)\s+Seasons?\)\s*$'
        )

        # Season: lines starting with [S.<season_id>]
        self.season_pattern = re.compile(
            r'^\[S\.(?P<season_id>\d+)\]\s+Season\s+(?P<season_number>\d+)\s+\((?P<eps_count>\d+)\s+Episodes?\)\s*$'
        )

        # Episode: lines starting with [E.<episode_id>]
        self.episode_pattern = re.compile(
            r'^\[E\.(?P<episode_id>\d+)\]\s+(?P<episode_title>.+?)\s*$'
        )

        # Flat episode pattern: lines starting with [S<season_number>E<download_number>]
        self.flat_episode_pattern = re.compile(
            r'^\[S(?P<season_number>\d+)E(?P<download_number>\d+)\]\s+(?P<title>.+?)\s*$'
        )

        if os.path.exists("/usr/bin/stdbuf"):
            self.stdbuf_exists = True
            logger.debug("[HIDIVE_MDNX_API] Using stdbuf to ensure live output streaming.")
        else:
            self.stdbuf_exists = False
            logger.debug("[HIDIVE_MDNX_API] stdbuf not found, using default command without buffering.")

        logger.info(f"[HIDIVE_MDNX_API] MDNX API initialized with: Path: {mdnx_path} | Service: {mdnx_service}")

    def process_console_output(self, output: str, add2queue: bool = True):
        logger.debug("[HIDIVE_MDNX_API] Processing console output...")
        tmp_dict = {}
        current_series_id = None
        current_season_key = None

        seasons_meta = {}
        episodes_by_season = {}
        download_map_by_season = {} # {"S1": {1:1, 2:2, ...}, "S2": {1:21, 2:22, ...}}
        flat_local_index = {} # {"S1": next_local_idx, "S2": ...}

        for raw in output.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith("[ERROR]") or line.startswith("[WARN]"):
                continue

            match = self.series_pattern.match(line)
            if match:
                info = match.groupdict()
                current_series_id = info["series_id"]
                tmp_dict[current_series_id] = {
                    "series": {
                        "series_id": info["series_id"],
                        "series_name": sanitize(info["series_name"]),
                        "seasons_count": str(info["seasons_count"]),
                    },
                    "seasons": {}
                }
                seasons_meta.clear()
                episodes_by_season.clear()
                download_map_by_season.clear()
                flat_local_index.clear()
                current_season_key = None
                continue

            if not current_series_id:
                continue

            match = self.season_pattern.match(line)
            if match:
                info = match.groupdict()
                season_key = f"S{int(info['season_number'])}"
                current_season_key = season_key
                seasons_meta[season_key] = {
                    "season_id": info["season_id"],
                    "season_name": f"Season {info['season_number']}",
                    "season_number": str(int(info["season_number"])),
                    "eps_count": str(int(info["eps_count"])),
                }
                episodes_by_season.setdefault(season_key, [])
                continue

            if current_season_key:
                match = self.episode_pattern.match(line)
                if match:
                    gd = match.groupdict()
                    episodes_by_season[current_season_key].append(
                        (gd["episode_id"], sanitize(gd["episode_title"]))
                    )
                    continue

            # collect global download numbers from flat list ([SxEy] Title)
            flat = self.flat_episode_pattern.match(line)
            if flat:
                gd = flat.groupdict()
                s_key = f"S{int(gd['season_number'])}"
                download_number = int(gd["download_number"])
                idx = flat_local_index.get(s_key, 0) + 1
                flat_local_index[s_key] = idx
                download_map_by_season.setdefault(s_key, {})[idx] = download_number
                continue

        if not current_series_id:
            logger.warning("[HIDIVE_MDNX_API] No HiDive series detected in output.")
            if add2queue:
                queue_manager.add(tmp_dict, self.queue_service)
            return tmp_dict

        total_episodes = 0
        for season_key, meta in sorted(seasons_meta.items(), key=lambda kv: int(kv[1]["season_number"])):
            season_id = meta["season_id"]
            episode_list = episodes_by_season.get(season_key, [])
            declared_count = int(meta.get("eps_count", len(episode_list)))

            while len(episode_list) < declared_count:
                idx_pad = len(episode_list) + 1
                episode_list.append((f"unknown-{season_id}-{idx_pad}", ""))

            episodes_dict = {}
            for idx, (episode_id, title) in enumerate(episode_list, start=1):

                # prefer global download number from flat list; fallback to local idx
                ep_download_num = download_map_by_season.get(season_key, {}).get(idx, idx)

                dubs_list, subs_list = self._probe_episode_streams(current_series_id, season_id, ep_download_num)

                episode_key = f"E{idx}"
                episodes_dict[episode_key] = {
                    "episode_number": str(idx),
                    "episode_number_download": str(ep_download_num),
                    "episode_name": sanitize(title) if title else f"Episode {idx}",
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
            text = (result.stdout or "") + "\n" + (result.stderr or "")
            logger.debug(f"[HIDIVE_MDNX_API] Probe output:\n{text}")
        except Exception as e:
            logger.error(f"[HIDIVE_MDNX_API] Probe failed (series {series_id} season {season_id} episode {episode_index}): {e}")
            return [], []

        available_dubs = []
        available_subs = []
        in_audios = False
        in_subs = False

        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                # end any active section on blank lines
                in_audios = False
                in_subs = False
                continue

            # allow lines like "[INFO] Audios:" or "Audios:" (any leading text)
            if re.search(r'Audios\s*:\s*', raw):
                in_audios = True
                in_subs = False
                tail = re.split(r'Audios\s*:\s*', raw, maxsplit=1)[-1].strip()
                if tail:
                    name_or_code = tail
                    code_found = None
                    for display_name, code in NAME_TO_CODE.items():
                        if display_name.lower() == name_or_code.strip().lower():
                            code_found = code.lower()
                            break
                    if not code_found:
                        low = name_or_code.strip().lower()
                        if low in CODE_TO_LOCALE:
                            code_found = low
                    if code_found:
                        available_dubs.append(code_found)
                continue

            # allow "Subs  :" or "Subs:" with varying spaces or prefixes (e.g., "[INFO] Subs  :")
            # TODO: Refactor this to helper functions or re-do it when not at %1 of the brain power
            if re.search(r'Subs\s*:\s*', raw):
                in_audios = False
                in_subs = True
                tail = re.split(r'Subs\s*:\s*', raw, maxsplit=1)[-1].strip()
                if tail:
                    locale_found = None
                    for loc in VALID_LOCALES:
                        if loc.lower() == tail.lower():
                            locale_found = loc
                            break
                    if not locale_found:
                        low = tail.lower()
                        if low in CODE_TO_LOCALE:
                            mapped = CODE_TO_LOCALE[low]
                            for loc in VALID_LOCALES:
                                if loc.lower() == mapped:
                                    locale_found = loc
                                    break
                            if not locale_found:
                                locale_found = mapped
                    if not locale_found:
                        for display_name, vals in LANG_MAP.items():
                            if display_name.lower() == tail.lower():
                                candidate = vals[1]
                                for loc in VALID_LOCALES:
                                    if loc.lower() == candidate.lower():
                                        locale_found = loc
                                        break
                                if not locale_found:
                                    locale_found = candidate
                                break
                    if locale_found:
                        available_subs.append(locale_found)
                continue

            if in_audios and line:
                name_or_code = line
                code_found = None
                for display_name, code in NAME_TO_CODE.items():
                    if display_name.lower() == name_or_code.strip().lower():
                        code_found = code.lower()
                        break
                if not code_found:
                    low = name_or_code.strip().lower()
                    if low in CODE_TO_LOCALE:
                        code_found = low
                if code_found:
                    available_dubs.append(code_found)
                continue

            if in_subs and line:
                tail = line
                locale_found = None
                for loc in VALID_LOCALES:
                    if loc.lower() == tail.lower():
                        locale_found = loc
                        break
                if not locale_found:
                    low = tail.lower()
                    if low in CODE_TO_LOCALE:
                        mapped = CODE_TO_LOCALE[low]
                        for loc in VALID_LOCALES:
                            if loc.lower() == mapped:
                                locale_found = loc
                                break
                        if not locale_found:
                            locale_found = mapped
                if not locale_found:
                    for display_name, vals in LANG_MAP.items():
                        if display_name.lower() == tail.lower():
                            candidate = vals[1]
                            for loc in VALID_LOCALES:
                                if loc.lower() == candidate.lower():
                                    locale_found = loc
                                    break
                            if not locale_found:
                                locale_found = candidate
                            break
                if locale_found:
                    available_subs.append(locale_found)
                continue

        seen = set()
        dubs_deduped = []
        for code in available_dubs:
            if code not in seen:
                seen.add(code)
                dubs_deduped.append(code)

        seen = set()
        subs_deduped = []
        for loc in available_subs:
            if loc not in seen:
                seen.add(loc)
                subs_deduped.append(loc)

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
            logger.error("[HIDIVE_MDNX_API] MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\HIDIVE_USERNAME\HIDIVE_PASSWORD\nExiting...")
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

                if "[mkvmerge Done]" in cleaned:
                    success = True

        if proc.returncode != 0:
            logger.error(f"[HIDIVE_MDNX_API] Download failed with exit code {proc.returncode}")
            return False

        if not success:
            logger.error("[HIDIVE_MDNX_API] Download did not report successful download. Assuming failure.")
            return False

        logger.info("[HIDIVE_MDNX_API] Download finished successfully.")
        return True