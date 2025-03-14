
import os
import sys
import logging
import requests
import shutil
import re
import json
from tqdm import tqdm
from zipfile import ZipFile
from json import load as JSload
import subprocess

with open("appdata/config/config.json", 'r') as config_file:
    config = JSload(config_file)

# App settings
LOG_FILE = config["app"]["LOG_FILE"]
SYSTEM = config["app"]["SYSTEM"]
TEMP_DIR = config["app"]["TEMP_DIR"]
BIN_DIR = config["app"]["BIN_DIR"]

# Dependency URLs
DEPENDENCY_URLS = config["dependency_urls"]

# MDNX config settings
MDNX_CONFIG = config["mdnx"]

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(),      # Logs to console
        logging.FileHandler(config["app"]["LOG_FILE"])  # Logs to a file
    ]
)

class QueueManager:
    def __init__(self, queue_path="appdata/config/queue.json"):
        self.queue_path = queue_path
        self.queue_data = self.load_queue()

    def load_queue(self):
        if os.path.exists(self.queue_path):
            try:
                with open(self.queue_path, "r", encoding="utf-8") as data:
                    return json.load(data)
            except json.JSONDecodeError:
                logging.error("Malformed JSON in queue file. Starting with an empty queue.")
                return {}
        return {}

    def save_queue(self):
        with open(self.queue_path, "w", encoding="utf-8") as f:
            json.dump(self.queue_data, f, indent=4, ensure_ascii=False)
        logging.info(f"Queue saved to {self.queue_path}.")

    def add(self, new_data: dict):
        for series_id, series_info in new_data.items():
            if series_id in self.queue_data:
                # Update existing entry:
                self.queue_data[series_id]["series"] = series_info["series"]
                self.queue_data[series_id]["seasons"].update(series_info["seasons"])
                self.queue_data[series_id]["episodes"].update(series_info["episodes"])
                logging.info(f"Updated series '{series_id}' in the queue.")
            else:
                # Add a new entry:
                self.queue_data[series_id] = series_info
                logging.info(f"Added series '{series_id}' to the queue.")
        self.save_queue()

    def remove(self, series_id: str):
        if series_id in self.queue_data:
            del self.queue_data[series_id]
            self.save_queue()
            logging.info(f"Removed series '{series_id}' from the queue.")
        else:
            logging.warning(f"Series '{series_id}' not found in the queue.")

    def output(self):
        return self.queue_data if self.queue_data else None

class MDNX_API:
    def __init__(self, mdnx_path, mdnx_service="crunchy"):
        logging.info(f"MDNX API initialized with path: {mdnx_path}")
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
                    "episode_name": cleaned_name
                }
                continue

        self.queue_manager.add(tmp_dict)
        return tmp_dict

    def auth(self):
        logging.info(f"Authenticating with {self.mdnx_service}...")

        if not self.username or not self.password:
            logging.error("MDNX service username or password not found.\nPlease check the config file and enter your credentials in the following keys:\nMDNX_SERVICE_USERNAME\nMDNX_SERVICE_PASSWORD")
            sys.exit(1)

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --auth --username {self.username} --password {self.password} --silentAuth"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)

        logging.info(result.stdout)
        return result.stdout

    def start_monitor(self, series_id: str):
        logging.info(f"Monitoring series with ID: {series_id}")

        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --srz {series_id}"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)
        logging.info(result.stdout)

        self.process_console_output(result.stdout)

        return result.stdout

    def stop_monitor(self, series_id: str):
        logging.info(f"Stopping monitor for series with ID: {series_id}")

        self.queue_manager.remove(series_id)

        return


def download_file(url, *, tmp_dir=TEMP_DIR, dest_dir=BIN_DIR):
    logging.info(f"Downloading file from: {url}")
    # extract the file name from the URL
    filename = os.path.basename(url)
    tmp_path = os.path.join(tmp_dir, filename)
    dest_path = os.path.join(dest_dir, filename)

    # create directories if they do not exist
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(dest_dir, exist_ok=True)

    # start the request and stream the content
    response = requests.get(url, stream=True)
    response.raise_for_status()  # raise an error for bad responses

    # get total file size from headers
    total_size = int(response.headers.get("content-length", 0))

    # write the file in chunks with a progress bar
    with open(tmp_path, "wb") as f, tqdm(
        total=total_size, unit="B", unit_scale=True, desc=filename, ncols=80
    ) as pbar:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive chunks
                f.write(chunk)
                pbar.update(len(chunk))

    # move the file from the temp directory to the destination
    shutil.move(tmp_path, dest_path)
    print(f"Download complete. File moved to: {dest_path}")
def extract_archive(archive_path, dest_dir=BIN_DIR):
    with ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(dest_dir)
    os.remove(archive_path)
    logging.info(f"Extracted archive to: {dest_dir}")
def check_dependencies():
    logging.info("Checking dependencies...")

    if not os.path.exists(BIN_DIR):
        logging.info(f"{BIN_DIR} not found. Creating...")
        os.makedirs(BIN_DIR)

    for dependency_name, dependency_dl_url in DEPENDENCY_URLS.items():
        if not os.path.exists(os.path.join(BIN_DIR, dependency_name)):
            logging.info(f"{dependency_name} not found. Downloading...")
            download_file(dependency_dl_url)
            logging.info(f"Extracting {dependency_name}...")
            extract_archive(os.path.join(BIN_DIR, f"{dependency_name}.zip"))

    logging.info("Dependencies check complete.")

def format_value(val):
    """
    Format the value based on its type:
    - Integers and floats are returned as-is.
    - Booleans are returned as 'true' or 'false' (YAML style).
    - Lists are formatted as ["elem1", "elem2", ...] with double quotes around strings.
    - Strings are wrapped in double quotes.
    """
    if isinstance(val, bool):
        return "true" if val else "false"
    elif isinstance(val, (int, float)):
        return str(val)
    elif isinstance(val, list):
        # Format each element in the list. If an element is a string, wrap it in quotes.
        formatted_elements = ', '.join([f'"{x}"' if isinstance(x, str) else str(x) for x in val])
        return f'[{formatted_elements}]'
    else:
        return f'"{val}"'
def update_mdnx_config():
    logging.info("Updating MDNX config files with new settings from config.json...")

    for mdnx_config_file, mdnx_config_settings in MDNX_CONFIG.items():
        file_path = os.path.join(BIN_DIR, "mdnx", "config", f"{mdnx_config_file}.yml")

        lines = []
        for setting_key, setting_value in mdnx_config_settings.items():
            formatted_value = format_value(setting_value)
            line = f"{setting_key}: {formatted_value}\n"
            lines.append(line)

        with open(file_path, "w") as file:
            file.writelines(lines)

        logging.info(f"Updated {file_path} with new settings.")

    logging.info("MDNX config updated.")


def app():
    mdnx_api = MDNX_API(mdnx_path=os.path.join(BIN_DIR, "mdnx", "aniDL.exe"))

    # Authenticate with MDNX service if needed
    if not os.path.exists(os.path.join(BIN_DIR, "mdnx", "config", "cr_token.yml")):
        mdnx_api.auth()

    queue_ids = tuple(mdnx_api.queue_manager.output().keys())

    for id in config["monitor-series-id"]:
        if id not in queue_ids:
            mdnx_api.start_monitor(id)
        else:
            logging.info(f"Series with ID: {id} is already being monitored.")

    for id in queue_ids:
        if id not in config["monitor-series-id"]:
            mdnx_api.stop_monitor(id)



if __name__ == "__main__":
    logging.info("App started.")
    check_dependencies()
    update_mdnx_config()
    app()