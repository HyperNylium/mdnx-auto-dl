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

    def process_console_output(self, output: str) -> dict:
        logger.info("[MDNX_API] Processing console output...")
        tmp_dict = {}

        # Process each line of the console output.
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            # Check for series information.
            series = self.series_pattern.match(line)
            if series:
                series_info = series.groupdict()
                current_series_id = series_info["series_id"]
                # Create a new entry in tmp_dict for this series.
                tmp_dict[current_series_id] = {
                    "series": series_info,
                    "seasons": {},
                    "episodes": {}
                }
                continue

            # Check for season information.
            season = self.season_pattern.match(line)
            if season and current_series_id is not None:
                season_info = season.groupdict()
                tmp_dict[current_series_id]["seasons"][season_info["season_id"]] = season_info
                continue

            # Check for episode information.
            episode = self.episode_pattern.match(line)
            if episode and current_series_id is not None:
                episode_info = episode.groupdict()
                # Clean up the episode name by splitting on the last occurrence of " - "
                parts = episode_info["full_episode_name"].rsplit(" - ", 1)
                if len(parts) > 1:
                    cleaned_name = parts[-1]
                else:
                    cleaned_name = episode_info["full_episode_name"]
                # Use ep_type+episode_number as key. Example, "E1".
                ep_key = f'{episode_info["ep_type"]}{episode_info["episode_number"]}'
                tmp_dict[current_series_id]["episodes"][ep_key] = {
                    "episode_number": episode_info["episode_number"],
                    "episode_name": cleaned_name,
                    "episode_downloaded": False
                }
                continue

        self.queue_manager.add(tmp_dict)

        logger.info("[MDNX_API] Console output processed.")
        return tmp_dict

    def test(self) -> None:
        logger.info("[MDNX_API] Testing MDNX API...")

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --srz GMEHME81V"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True).stdout
        logger.info(f"[MDNX_API] MDNX API test resault:\n{result}")

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
            logger.error("[MDNX_API] MDNX service username or password not found.\nPlease check the config.json file and enter your credentials in the following keys:\nMDNX_SERVICE_USERNAME\nMDNX_SERVICE_PASSWORD.\nExiting...")
            sys.exit(1)

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --auth --username {self.username} --password {self.password} --silentAuth"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)
        logger.info(f"[MDNX_API] Console output for auth process:\n{result.stdout}")

        logger.info(f"[MDNX_API] Authentication with {self.mdnx_service} complete.")
        return result.stdout

    def start_monitor(self, series_id: str) -> str:
        logger.info(f"[MDNX_API] Monitoring series with ID: {series_id}")

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --srz {series_id}"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)
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

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --srz {series_id}"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)
        logger.info(f"[MDNX_API] Console output for update_monitor process:\n{result.stdout}")

        self.process_console_output(result.stdout)

        logger.info(f"[MDNX_API] Updating monitor for series with ID: {series_id} complete.")
        return result.stdout