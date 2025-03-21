import re
import sys
import subprocess

# Custom imports
from .QueueManager import QueueManager
from .Vars import logger, config



class MDNX_API:
    def __init__(self, mdnx_path, config=config, mdnx_service="crunchy"):
        logger.info(f"MDNX API initialized with path: {mdnx_path}")
        self.mdnx_path = mdnx_path
        self.mdnx_service = mdnx_service
        self.username = config["app"]["MDNX_SERVICE_USERNAME"]
        self.password = config["app"]["MDNX_SERVICE_PASSWORD"]
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

        if config["app"]["MDNX_API_SKIP_TEST"] == False:
            self.test()
        else:
            logger.info("MDNX API test skipped by user.")

    def process_console_output(self, output: str):
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
        return tmp_dict

    def test(self):
        logger.info("Testing MDNX API...")

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --srz GMEHME81V"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True).stdout
        logger.info(f"MDNX API test resault:\n{result}")

        # Check if the output contains authentication errors
        error_triggers = ["invalid_grant", "Token Refresh Failed", "Authentication required"]
        if any(trigger in result for trigger in error_triggers):
            logger.info("Authentication error detected. Forcing re-authentication...")
            self.auth()
        else:
            logger.info("MDNX API test successful.")

        return


    def auth(self):
        logger.info(f"Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            logger.error("MDNX service username or password not found.\nPlease check the config file and enter your credentials in the following keys:\nMDNX_SERVICE_USERNAME\nMDNX_SERVICE_PASSWORD")
            sys.exit(1)

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --auth --username {self.username} --password {self.password} --silentAuth"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)

        logger.info(result.stdout)
        return result.stdout

    def start_monitor(self, series_id: str):
        logger.info(f"Monitoring series with ID: {series_id}")

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --srz {series_id}"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)
        logger.info(result.stdout)

        self.process_console_output(result.stdout)

        return result.stdout

    def stop_monitor(self, series_id: str):
        logger.info(f"Stopping monitor for series with ID: {series_id}")

        self.queue_manager.remove(series_id)

        return