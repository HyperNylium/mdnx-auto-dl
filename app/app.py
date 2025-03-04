
import os
import logging
import requests
import shutil
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

class MDNX_API:
    def __init__(self, mdnx_path):
        logging.info(f"MDNX API initialized with path: {mdnx_path}")
        self.mdnx_path = mdnx_path
        self.mdnx_service = "crunchy"

    def search(self, query):
        logging.info(f"Searching for: {query}")
        tmp_cmd = f"{self.mdnx_path} --service {self.mdnx_service} --search {query}"
        result = subprocess.run(tmp_cmd, capture_output=True, text=True)
        del tmp_cmd
        return result.stdout


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

    print(mdnx_api.search("naruto"))

if __name__ == "__main__":
    logging.info("App started.")
    check_dependencies()
    update_mdnx_config()
    app()