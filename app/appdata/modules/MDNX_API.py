import os
import re
import sys
import subprocess

# Custom imports
from .QueueManager import QueueManager
from .Vars import logger, config



class MDNX_API:
    def __init__(self, mdnx_path, config=config, mdnx_service="crunchy") -> None:
        logger.info(f"[MDNX_API] MDNX API initialized with\nPath: {mdnx_path}\nService: {mdnx_service}")
        self.mdnx_path = mdnx_path
        self.mdnx_service = mdnx_service
        self.username = str(config["app"]["MDNX_SERVICE_USERNAME"])
        self.password = str(config["app"]["MDNX_SERVICE_PASSWORD"])
        self.queue_manager = QueueManager()

        self.series_pattern = re.compile(
            r'^\[Z:(?P<series_id>\w+)\]\s+(?P<series_name>.+?)\s+\(Seasons:\s*(?P<seasons_count>\d+),\s*EPs:\s*(?P<eps_count>\d+)\)'
        )
        self.season_pattern = re.compile(
            r'^\[S:(?P<season_id>\w+)\]\s+(?P<season_name>.+?)\s+\(Season:\s*(?P<season_number>\d+)\)'
        )
        # Episodes: lines starting with [E...] or [S...] (without the colon after S)
        self.episode_pattern = re.compile(
            r'^\[(?P<ep_type>E|S)(?P<episode_number>\d+)\]\s+(?P<full_episode_name>.+?)\s+\['
        )

        # Skip MDNX API test if user wants to
        if config["app"]["MDNX_API_SKIP_TEST"] == False:
            self.test()
        else:
            logger.info("[MDNX_API] MDNX API test skipped by user.")

    def process_console_output(self, output: str, add2queue: bool = True) -> dict:
        logger.info("[MDNX_API] Processing console output...")

        tmp_dict = {}
        episode_counters = {} # maps season key ("S1", "S2", etc) to episode counter
        current_series_id = None

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check for series information.
            series = self.series_pattern.match(line)
            if series:
                info = series.groupdict()
                current_series_id = info["series_id"]
                tmp_dict[current_series_id] = {
                    "series": info,
                    "seasons": {}
                }
                continue

            # Check for season information.
            season = self.season_pattern.match(line)
            if season and current_series_id is not None:
                info = season.groupdict()
                season_num = info.get("season_number") or info.get("season")
                season_key = f"S{season_num}"
                tmp_dict[current_series_id]["seasons"][season_key] = {
                    **info,
                    "episodes": {}
                }
                # Initialize the episode counter for this season.
                episode_counters[season_key] = 1
                continue

            # Check for episode information.
            episode = self.episode_pattern.match(line)
            if episode and current_series_id is not None:
                ep_info = episode.groupdict()

                # grab the season number from the episode line itself
                match = re.search(r'- Season (\d+) -', line)
                if not match:
                    logger.warning(f"[MDNX_API] Season not found in episode line: {line}")
                    continue

                season_num = match.group(1)
                season_key = f"S{season_num}"

                # ensure season entry exists even if header was missing
                if season_key not in tmp_dict[current_series_id]["seasons"]:
                    tmp_dict[current_series_id]["seasons"][season_key] = {
                        "season_id": None,
                        "season_name": None,
                        "season_number": season_num,
                        "episodes": {}
                    }
                    episode_counters[season_key] = 1

                counter = episode_counters[season_key]

                # clean the title
                parts = ep_info["full_episode_name"].rsplit(" - ", 1)
                cleaned_name = parts[-1] if len(parts) > 1 else ep_info["full_episode_name"]

                ep_key = f"E{counter}"
                tmp_dict[current_series_id]["seasons"][season_key]["episodes"][ep_key] = {
                    "episode_number": str(counter),
                    "episode_name":   cleaned_name
                }
                episode_counters[season_key] += 1
                continue

        logger.info("[MDNX_API] Console output processed.")

        if add2queue:
            logger.info("[MDNX_API] Adding processed console output to QueueManager...")
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
            logger.error("[MDNX_API] MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nMDNX_SERVICE_USERNAME\nMDNX_SERVICE_PASSWORD\nExiting...")
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
        logger.info(f"[MDNX_API] Console output for start_monitor process:\n{result.stdout}")

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
        logger.info(f"[MDNX_API] Console output for update_monitor process:\n{result.stdout}")

        self.process_console_output(result.stdout)

        logger.info(f"[MDNX_API] Updating monitor for series with ID: {series_id} complete.")
        return result.stdout

    def download_episode(self, series_id: str, season_id: str, episode_number: str) -> bool:
        logger.info(f"[MDNX_API] Downloading episode {episode_number} for series {series_id} season {season_id}")

        tmp_cmd = [self.mdnx_path, "--service", self.mdnx_service, "--srz", series_id, "-s", season_id, "-e", episode_number]

        if os.path.exists("/usr/bin/stdbuf"):
            logger.info("[MDNX_API] Using stdbuf to ensure live output streaming.")
            cmd = ["stdbuf", "-oL", "-eL", *tmp_cmd]
        else:
            logger.info("[MDNX_API] stdbuf not found, using default command without buffering.")
            cmd = tmp_cmd

        logger.info(f"[MDNX_API] Command to execute: {' '.join(cmd)}")

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                logger.info("[MDNX_API][multidownload-nx] %s", line.rstrip())

        success = None
        if proc.returncode == 0:
            logger.info("[MDNX_API] Download finished successfully.")
            success = True
        else:
            logger.error(f"[MDNX_API] Download failed with exit code {proc.returncode}")
            success = False

        return success
