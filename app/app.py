
import os
import logging
import requests
import shutil
from zipfile import ZipFile
from tqdm import tqdm
from json import load as JSload

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

def download_file(url, *, tmp_dir=TEMP_DIR, dest_dir=BIN_DIR):
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
    print(f"Extracted archive to: {dest_dir}")


def check_dependencies():
    logging.info("Checking dependencies...")

    if not os.path.exists(BIN_DIR):
        logging.info(f"{BIN_DIR} not found. Creating...")
        os.makedirs(BIN_DIR)

    if not os.path.exists(os.path.join(BIN_DIR, "Bento4-SDK")):
        logging.info("Bento4-SDK not found. Downloading...")
        download_file(DEPENDENCY_URLS["Bento4-SDK"])
        extract_archive(os.path.join(BIN_DIR, "Bento4-SDK.zip"))

    if not os.path.exists(os.path.join(BIN_DIR, "ffmpeg")):
        logging.info("ffmpeg not found. Downloading...")
        download_file(DEPENDENCY_URLS["ffmpeg"])
        extract_archive(os.path.join(BIN_DIR, "ffmpeg.zip"))

    if not os.path.exists(os.path.join(BIN_DIR, "mdnx")):
        logging.info("mdnx not found. Downloading...")
        download_file(DEPENDENCY_URLS["mdnx"])
        extract_archive(os.path.join(BIN_DIR, "mdnx.zip"))
    
    if not os.path.exists(os.path.join(BIN_DIR, "mkvtoolnix")):
        logging.info("mkvtoolnix not found. Downloading...")
        download_file(DEPENDENCY_URLS["mkvtoolnix"])
        extract_archive(os.path.join(BIN_DIR, "mkvtoolnix.zip"))

    logging.info("Dependencies check complete.")



if __name__ == "__main__":
    logging.info("App started.")
    check_dependencies()