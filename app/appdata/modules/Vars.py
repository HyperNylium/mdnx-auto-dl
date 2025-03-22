import os
import json
import shutil
import logging
import requests
from tqdm import tqdm
from zipfile import ZipFile


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
        logging.StreamHandler(),                        # Logs to console
        logging.FileHandler(config["app"]["LOG_FILE"])  # Logs to a file
    ]
)

# Create a logger for all modules to use
logger = logging.getLogger(__name__)



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