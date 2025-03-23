import os
import sys
import json
import shutil
import logging
import requests
from zipfile import ZipFile
from string import Template
from io import TextIOWrapper


CONFIG_PATH = "appdata/config/config.json"
QUEUE_PATH = "appdata/config/queue.json"


# Load the config file
with open(CONFIG_PATH, 'r') as config_file:
    config = json.load(config_file)

# App settings
LOG_FILE = config["app"]["LOG_FILE"]
TEMP_DIR = config["app"]["TEMP_DIR"]
BIN_DIR = config["app"]["BIN_DIR"]

# Dependency URLs
DEPENDENCY_URLS = config["dependency_urls"]

# MDNX config settings
MDNX_CONFIG = config["mdnx"]

# Dynamic paths
MDNX_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "mdnx", "aniDL.exe")
MDNX_SERVICE_CR_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "cr_token.yml")


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(TextIOWrapper(sys.stdout.buffer, encoding="utf-8")),
        logging.FileHandler(LOG_FILE, encoding="utf-8")
    ]
)

# Create a logger for all modules to use
logger = logging.getLogger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Call the default excepthook to handle the exception if it's a KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def download_file(url, *, tmp_dir=TEMP_DIR, dest_dir=BIN_DIR):
    logger.info(f"[Vars] Downloading file from: {url}")
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

    # write the file in chunks without a progress bar
    with open(tmp_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive chunks
                f.write(chunk)

    # move the file from the temp directory to the destination
    shutil.move(tmp_path, dest_path)
    logger.info(f"[Vars] Download complete. File moved to: {dest_path}")

def extract_archive(archive_path, dest_dir=BIN_DIR):
    logger.info(f"[Vars] Extracting archive: {archive_path}")
    with ZipFile(archive_path, "r") as zip_ref:
        zip_ref.extractall(dest_dir)
    os.remove(archive_path)
    logger.info(f"[Vars] Extracted archive to: {dest_dir}")

def check_dependencies():
    logger.info("[Vars] Checking dependencies...")

    if not os.path.exists(BIN_DIR):
        logger.info(f"[Vars] {BIN_DIR} not found. Creating directory...")
        os.makedirs(BIN_DIR)

    for dependency_name, dependency_dl_url in DEPENDENCY_URLS.items():
        if not os.path.exists(os.path.join(BIN_DIR, dependency_name)):
            logger.info(f"[Vars] {dependency_name} not found. Downloading...")
            download_file(dependency_dl_url)
            logger.info(f"[Vars] Extracting {dependency_name}...")
            extract_archive(os.path.join(BIN_DIR, f"{dependency_name}.zip"))

    logger.info("[Vars] Dependencies check complete.")

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
    logger.info("[Vars] Updating MDNX config files with new settings from config.json...")

    for mdnx_config_file, mdnx_config_settings in MDNX_CONFIG.items():
        file_path = os.path.join(BIN_DIR, "mdnx", "config", f"{mdnx_config_file}.yml")

        lines = []
        for setting_key, setting_value in mdnx_config_settings.items():
            formatted_value = format_value(setting_value)
            line = f"{setting_key}: {formatted_value}\n"
            lines.append(line)

        with open(file_path, "w") as file:
            file.writelines(lines)

        logger.info(f"[Vars] Updated {file_path} with new settings.")

    logger.info("[Vars] MDNX config updated.")

def update_app_config(key: str, value):
    global config

    for Property in ["app"]:
        if Property in config and key in config[Property]:
            config[Property][key] = value
            break
    else:
        logger.error(f"[Vars] Error while writing to the config file\nProperty: {Property}\nKey: {key}\nValue: {value}")
        return

    with open(CONFIG_PATH, 'w') as config_file:
        json.dump(config, config_file, indent=4)

def log_manager(log_file_path=LOG_FILE, max_lines: int = 50000, keep_lines: int = 5000) -> None:
    try:
        with open(log_file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        
        total_lines = len(lines)
        if total_lines > max_lines:
            # Keep only the last 'keep_lines' lines.
            new_lines = lines[-keep_lines:]
            with open(log_file_path, 'w', encoding='utf-8') as file:
                file.writelines(new_lines)
            logger.info(f"Log file truncated: was {total_lines} lines, now {keep_lines} lines kept.")
        else:
            logger.info("Log file is within the allowed size; no truncation performed.")
    except Exception as e:
        logger.error(f"Error managing log file: {e}")

def get_episode_file_path(queue, series_id, season_key, episode_key, base_dir, extension=".mkv"):
    """
    Constructs the full file path for an episode using the dynamic file naming.
    
    The folder structure is:
      {base_dir}/{series_name}/S{season}/{file_name}

    Where file_name is generated based on the template from "mdnx > cli-defaults > fileName" config.
    """
    # Get data from the queue.
    series_name = queue[series_id]["series"]["series_name"]
    season = queue[series_id]["seasons"][season_key]["season_number"]
    episode = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_number"]
    episode_name = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_name"]

    # Generate the file name using the template.
    file_name = get_episode_naming_template(series_name, season, episode, episode_name, extension)

    # Build the season folder name (for folder organization, e.g., "S1")
    season_folder = f"S{int(season)}"

    # Combine to form the full file path.
    file_path = os.path.join(base_dir, series_name, season_folder, file_name)
    return file_path

def get_episode_naming_template(series_title, season, episode, episode_name, extension):
    """
    Generates a file name based on the template provided in config.json.
    
    The template can include the following tokens:
      - ${seriesTitle}   : The series name.
      - ${season}        : The season number (we’ll pad this to two digits).
      - ${episode}       : The episode number (padded to two digits).
      - ${episodeName}   : The episode title.
      
    For example, with the default template:
      "${seriesTitle} - S${season}E${episode}"
    and given:
      series_title = "Solo Leveling"
      season = 1
      episode = 1
      episode_name = "I'm Used to It"
      
    The output will be:
      "Solo Leveling - S01E01.mkv"
    """
    # Read the fileName template from your config
    file_template = str(config["mdnx"]["cli-defaults"]["fileName"])

    # Create a Template object
    template_obj = Template(file_template)

    # Prepare the substitution dictionary.
    substitutions = {
        "seriesTitle": series_title,
        "season": str(int(season)).zfill(2),
        "episode": str(int(episode)).zfill(2),
        "episodeName": episode_name
    }

    # Perform the substitution.
    file_name = template_obj.safe_substitute(substitutions)

    # Append the extension if not already present.
    if not file_name.endswith(extension):
        file_name = f"{file_name}{extension}"

    return file_name

def iter_episodes(queue_data: dict):
    for series_id, series_info in queue_data.items():
        for season_key, season_info in series_info["seasons"].items():
            for episode_key, episode_info in season_info["episodes"].items():
                yield series_id, season_key, episode_key, episode_info