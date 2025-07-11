import os
import re
import sys
import pwd
import grp
import json
import logging
from string import Template
from io import TextIOWrapper


CONFIG_PATH = os.getenv("CONFIG_FILE", "appdata/config/config.json")
QUEUE_PATH = os.getenv("QUEUE_FILE", "appdata/config/queue.json")


# Load the config file
with open(CONFIG_PATH, 'r') as config_file:
    config = json.load(config_file)

# App settings
LOG_FILE = config["app"]["LOG_FILE"]
TEMP_DIR = config["app"]["TEMP_DIR"]
BIN_DIR = config["app"]["BIN_DIR"]

# MDNX config settings
MDNX_CONFIG = config["mdnx"]

# Dynamic paths
MDNX_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "mdnx", "aniDL")
MDNX_SERVICE_CR_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "cr_token.yml")

# Regular expression to match invalid characters in filenames
INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')


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
    # skip logging for KeyboardInterrupt and SystemExit. Use the default handler.
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

def refresh_queue(mdnx_api):
    logger.info("[Vars] Getting the current queue IDs...")
    queue_output = mdnx_api.queue_manager.output()
    if queue_output is not None:
        queue_ids = set(queue_output.keys())
    else:
        queue_ids = set()

    monitor_ids = set(config["monitor-series-id"])
    if not monitor_ids and not queue_ids:
        logger.info("[Vars] No series to monitor or stop monitoring.\nPlease add series IDs to 'monitor-series-id' in the config file to start monitoring.\nExiting...")
        sys.exit(1)

    # Start or update monitors
    logger.info("[Vars] Checking to see if any series need to be monitored...")
    for series_id in monitor_ids:
        if series_id not in queue_ids:
            logger.info(f"[Vars] Starting to monitor series with ID: {series_id}")
            mdnx_api.start_monitor(series_id)
        else:
            logger.info(f"[Vars] Series with ID: {series_id} is already being monitored. Updating with new data...")
            mdnx_api.update_monitor(series_id)

    # Stop monitors for IDs no longer in config
    logger.info("[Vars] Checking to see if any series need to be stopped from monitoring...")
    for series_id in queue_ids:
        if series_id not in monitor_ids:
            logger.info(f"[Vars] Stopping monitor for series with ID: {series_id}")
            mdnx_api.stop_monitor(series_id)

    logger.info("[Vars] MDNX queue refresh complete.")

    return True

def sanitize_cr_filename(name: str) -> str:
    """
    Replace every invalid character with '_' (one-for-one, preserving runs)
    to exactly mirror multidownload-nx output when it encounters invalid characters
    such as <, >, :, ", /, \, |, ?, *.
    """
    sanitized = INVALID_CHARS_RE.sub("_", name)
    logger.info(f"[Vars] Sanitize CR filename '{name}' to '{sanitized}'")
    return sanitized

def sanitize_destination_filename(segment: str) -> str:
    """
    Prepare a path segment for your the filesystem:
      - Replace invalid chars (and any underscores) with spaces
      - Collapse runs of whitespace into single spaces
      - Trim leading/trailing spaces
    """
    cleaned = INVALID_CHARS_RE.sub(" ", segment)
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned != segment:
        logger.info(f"[Vars] Sanitize destination '{segment}' to '{cleaned}'")
    return cleaned

def get_running_user():
    uid  = os.getuid()   # real UID
    gid  = os.getgid()   # real GID
    euid = os.geteuid()  # effective UID (after set-uid, if any)
    egid = os.getegid()  # effective GID

    user  = pwd.getpwuid(uid).pw_name
    group = grp.getgrgid(gid).gr_name

    logger.info(f"[Vars] Running as UID={uid} ({user}), GID={gid} ({group})")
    logger.info(f"[Vars] Effective UID={euid}, effective GID={egid}")

    return (uid, user, gid, group, euid, egid)

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

def build_folder_structure(base_dir: str, series_title: str, season: str, episode: str, episode_name: str, extension: str = ".mkv") -> str:
    template_str = str(config["app"]["FOLDER_STRUCTURE"])

    substitutes = {
        "seriesTitle": series_title,
        "season": str(int(season)),
        "seasonPadded": str(int(season)).zfill(2),
        "episode": str(int(episode)),
        "episodePadded": str(int(episode)).zfill(2),
        "episodeName": episode_name
    }

    raw_path = Template(template_str).safe_substitute(substitutes)

    # split on "/" so templates look identical on every OS
    parts = []
    for part in raw_path.split("/"):
        if not part:
            continue
        parts.append(sanitize_destination_filename(part))

    full_path = os.path.join(base_dir, *parts)

    # Add extension if the user omitted it
    if not full_path.lower().endswith(extension.lower()):
        full_path = f"{full_path}{extension}"

    return full_path

def get_episode_file_path(queue, series_id, season_key, episode_key, base_dir, extension=".mkv"):
    # Get data from the queue.
    raw_series = queue[series_id]["series"]["series_name"]
    season = queue[series_id]["seasons"][season_key]["season_number"]
    episode = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_number"]
    raw_episode_name = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_name"]

    # Build the folder structure and file name.
    file_name = build_folder_structure(base_dir, raw_series, season, episode, raw_episode_name, extension)

    # Combine to form the full file path.
    return file_name

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
                yield series_id, season_key, episode_key, season_info, episode_info