import os
import re
import sys
import pwd
import grp
import json
import logging
import subprocess
from string import Template
from io import TextIOWrapper
from collections import OrderedDict


CONFIG_PATH = os.getenv("CONFIG_FILE", "appdata/config/config.json")
QUEUE_PATH = os.getenv("QUEUE_FILE", "appdata/config/queue.json")


def merge_config(defaults: dict, overrides: dict) -> dict:
    if not isinstance(defaults, dict) or not isinstance(overrides, dict):
        if overrides is not None:
            return overrides
        else:
            return defaults

    merged = {}
    for key in (defaults.keys() | overrides.keys()):
        default_value = defaults.get(key)
        override_value = overrides.get(key)

        if isinstance(default_value, dict) and isinstance(override_value, dict):
            merged[key] = merge_config(default_value, override_value)
        elif override_value is None:
            merged[key] = default_value
        else:
            merged[key] = override_value

    return merged

def output_effective_config(config, max_chunk=8000):
    logger.info("[Vars] Effective config: ")
    formatted_json = json.dumps(config, indent=4, sort_keys=True)
    for line in formatted_json.splitlines():
        for i in range(0, len(line), max_chunk):
            logger.info(line[i:i+max_chunk])

# Default config values in case config.json is missing any keys.
CONFIG_DEFAULTS = {
    "cr_monitor_series_id": [],
    "hidive_monitor_series_id": [],
    "app": {
        "TEMP_DIR": "/app/appdata/temp",
        "BIN_DIR": "/app/appdata/bin",
        "LOG_FILE": "/app/appdata/logs/app.log",
        "DATA_DIR": "/data",
        "CR_ENABLED": True,
        "CR_USERNAME": "",
        "CR_PASSWORD": "",
        "HIDIVE_ENABLED": False,
        "HIDIVE_USERNAME": "",
        "HIDIVE_PASSWORD": "",
        "BACKUP_DUBS": ["zho"],
        "FOLDER_STRUCTURE": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}",
        "CHECK_MISSING_DUB_SUB": True,
        "CHECK_MISSING_DUB_SUB_TIMEOUT": 300,
        "CHECK_FOR_UPDATES_INTERVAL": 3600,
        "BETWEEN_EPISODE_DL_WAIT_INTERVAL": 30,
        "CR_FORCE_REAUTH": False,
        "CR_SKIP_API_TEST": False,
        "HIDIVE_FORCE_REAUTH": False,
        "HIDIVE_SKIP_API_TEST": False,
        "NOTIFICATION_PREFERENCE": "none",
        "ONLY_CREATE_QUEUE": False,
        "LOG_LEVEL": "info",
        "NTFY_SCRIPT_PATH": "/app/appdata/config/ntfy.sh",
        "SMTP_FROM": "",
        "SMTP_TO": "",
        "SMTP_HOST": "",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_PORT": 587,
        "SMTP_STARTTLS": True,
        "MEDIASERVER_TYPE": None,
        "MEDIASERVER_URL": None,
        "MEDIASERVER_TOKEN": None,
        "MEDIASERVER_URL_OVERRIDE": False,
    },
    "mdnx": {
        "bin-path": {
            "ffmpeg": "ffmpeg",
            "ffprobe": "ffprobe",
            "mkvmerge": "mkvmerge",
            "mp4decrypt": "/app/appdata/bin/Bento4-SDK/bin/mp4decrypt"
        },
        "cli-defaults": {
            "q": 0,
            "partsize": 3,
            "dubLang": [
                "jpn",
                "eng"
            ],
            "dlsubs": [
                "en"
            ],
            "defaultAudio": "jpn",
            "defaultSub": "eng",
            "vstream": "androidtv",
            "astream": "androidtv",
            "tsd": False
        },
        "dir-path": {
            "content": "/app/appdata/temp",
            "fonts": "./fonts/"
        }
    }
}

# Load the config file
with open(CONFIG_PATH, 'r') as config_file:
    LOCAL_CONFIG = json.load(config_file)

config = merge_config(defaults=CONFIG_DEFAULTS, overrides=LOCAL_CONFIG)

del LOCAL_CONFIG

# App settings
LOG_FILE = config["app"]["LOG_FILE"]
TEMP_DIR = config["app"]["TEMP_DIR"]
DATA_DIR = config["app"]["DATA_DIR"]
BIN_DIR = config["app"]["BIN_DIR"]

# MDNX config settings
MDNX_CONFIG = config["mdnx"]

# Dynamic paths
MDNX_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "mdnx", "aniDL")
MDNX_SERVICE_CR_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "cr_token.yml")
MDNX_SERVICE_HIDIVE_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "hd_new_token.yml")

# Regular expression to match invalid characters in filenames
INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

# Language mapping for MDNX
LANG_MAP = {
    "English": ["eng", "en"],
    "English (India)": ["eng", "en-IN"],
    "Spanish": ["spa", "es-419"],
    "Castilian": ["spa-ES", "es-ES"],
    "Portuguese": ["por", "pt-BR"],
    "Portuguese (Portugal)": ["por", "pt-PT"],
    "French": ["fra", "fr"],
    "German": ["deu", "de"],
    "Arabic": ["ara-ME", "ar"],
    "Arabic (Saudi Arabia)": ["ara", "ar"],
    "Italian": ["ita", "it"],
    "Russian": ["rus", "ru"],
    "Turkish": ["tur", "tr"],
    "Hindi": ["hin", "hi"],
    "Chinese (Mandarin, PRC)": ["cmn", "zh"],
    "Chinese (Mainland China)": ["zho", "zh-CN"],
    "Chinese (Taiwan)": ["chi", "zh-TW"],
    "Chinese (Hong-Kong)": ["zh-HK", "zh-HK"],
    "Korean": ["kor", "ko"],
    "Catalan": ["cat", "ca-ES"],
    "Polish": ["pol", "pl-PL"],
    "Thai": ["tha", "th-TH"],
    "Tamil (India)": ["tam", "ta-IN"],
    "Malay (Malaysia)": ["may", "ms-MY"],
    "Vietnamese": ["vie", "vi-VN"],
    "Indonesian": ["ind", "id-ID"],
    "Telugu (India)": ["tel", "te-IN"],
    "Japanese": ["jpn", "ja"],
}

# This will look like: {"English": "en", "Spanish": "es-419", ...}
NAME_TO_CODE = {}
for name, vals in LANG_MAP.items():
    NAME_TO_CODE[name] = vals[0] # vals[0] is the code

# This will look like: {"en", "es-419", ...}
VALID_LOCALES = set()
for vals in LANG_MAP.values():
    VALID_LOCALES.add(vals[1]) # vals[1] is the locale

# This will look like: {"eng": "en", "spa": "es-419", ...}
CODE_TO_LOCALE = {}
for name, vals in LANG_MAP.items():
    code = vals[0].lower()
    loc = vals[1].lower()
    CODE_TO_LOCALE[code] = loc

# Set up logging
LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}
LOG_LEVEL = LEVEL_MAP.get(config["app"]["LOG_LEVEL"].upper(), "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format='[%(asctime)s] %(message)s',
    datefmt='%I:%M:%S %p %d/%m/%Y',
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

def format_duration(seconds: int) -> str:
    units = [
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1),
    ]

    parts = []
    remaining = seconds
    for name, size in units:
        qty, remaining = divmod(remaining, size)
        if qty:
            parts.append(f"{qty} {name}{'' if qty == 1 else 's'}")

    if not parts:
        return "0 seconds"
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + f" and {parts[-1]}"

def select_dubs(episode_info: dict):
    desired_dubs = set()
    for lang in config["mdnx"]["cli-defaults"]["dubLang"]:
        desired_dubs.add(lang)

    backup_dubs = set()
    for lang in config["app"]["BACKUP_DUBS"]:
        backup_dubs.add(lang)

    available_dubs = set()
    for dub in episode_info["available_dubs"]:
        available_dubs.add(dub)

    logger.debug(f"[Vars] Desired dubs: {desired_dubs}")
    logger.debug(f"[Vars] Backup dubs: {backup_dubs}")
    logger.debug(f"[Vars] Available dubs: {available_dubs}")

    # If desired dub is available, use the default already present.
    if desired_dubs & available_dubs:
        logger.debug(f"[Vars] Desired dubs available: {desired_dubs & available_dubs}")
        return None

    # If backups are available but not the desired dubs, override with that intersection.
    if backup_dubs & available_dubs:
        logger.debug(f"[Vars] Desired dubs not available, but backup dubs are: {backup_dubs & available_dubs}")
        return list(backup_dubs & available_dubs)

    # Otherwise fall back to the alphabetically first available dub.
    if available_dubs:
        logger.debug(f"[Vars] Neither desired nor backup dubs are available. Falling back to first available dub.")
        first_dub = next(iter(sorted(available_dubs)))
        return [first_dub]

    # No dubs at all, which is unexpected tbh.
    # But, you never know with Crunchyroll...
    # Will skip the episode.
    logger.debug("[Vars] No dubs available at all for this episode. Skipping it.")
    return False

def probe_streams(file_path: str, timeout: int):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path]

    logger.debug(f"[Vars] Running ffprobe on {file_path} with command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        logger.error(f"[Vars] ffprobe timed out after {timeout}s on {file_path}")
        return set(), set()

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        logger.error(f"[Vars] ffprobe JSON decode error on {file_path}: {e}")
        return set(), set()

    if data == {}: # no streams found
        logger.error(f"[Vars] ffprobe found no dubs/subs for {file_path}")
        return set(), set()

    logger.debug(f"[Vars] ffprobe output for {file_path}: {data}")

    audio_langs = set()
    sub_langs = set()

    for stream in data.get("streams", []):
        tags = stream.get("tags", {})
        raw_lang = str(tags.get("language", "")).strip().lower()
        title = tags.get("title", "").strip()

        mapped_audio = None
        mapped_sub = None

        # if the title matches one of the LANG_MAP keys, get its dub and sub codes
        if title in LANG_MAP:
            # LANG_MAP[title] == ["dub_code", "sub_code"]
            mapped_audio = LANG_MAP[title][0].lower()
            mapped_sub = LANG_MAP[title][1].lower()

        if stream.get("codec_type") == "audio":
            if mapped_audio is not None:
                lang = mapped_audio
            else:
                lang = raw_lang

            audio_langs.add(lang)

        elif stream.get("codec_type") == "subtitle":
            if mapped_sub is not None:
                lang = mapped_sub

            elif raw_lang in CODE_TO_LOCALE:
                lang = CODE_TO_LOCALE[raw_lang]

            else:
                lang = raw_lang

            sub_langs.add(lang)

    logger.debug(f"[Vars] Probed {file_path}: audio languages: {audio_langs}, subtitle languages: {sub_langs}")

    return audio_langs, sub_langs

def sanitize(segment: str) -> str:
    """
    Prepare a path segment for your the filesystem:
      - Replace invalid chars with spaces
      - Collapse runs of whitespace into single spaces
      - Trim leading/trailing spaces
    """
    cleaned = INVALID_CHARS_RE.sub(" ", segment)
    cleaned = cleaned.replace("_", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if cleaned != segment:
        logger.debug(f"[Vars] Sanitized '{segment}' to '{cleaned}'")
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

        logger.debug(f"[Vars] Updated {file_path} with new settings.")

    logger.info("[Vars] MDNX config updated.")

def update_app_config(key: str, value):
    global config

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            on_disk = json.load(f, object_pairs_hook=OrderedDict)
    except Exception as e:
        logger.error(f"[Vars] Failed to read config file: {e}")
        return False

    app_section = on_disk.get("app")
    if not isinstance(app_section, dict):
        logger.error("[Vars] Invalid config: missing 'app' object.")
        return False

    app_section[key] = value

    # Reorder "app" section according to CONFIG_DEFAULTS["app"] key order.
    # Keys not present in defaults are appended in their current relative order.
    try:
        defaults_app = CONFIG_DEFAULTS.get("app", {})
        ordered_app = OrderedDict()

        for default_key in defaults_app.keys():
            if default_key in app_section:
                ordered_app[default_key] = app_section[default_key]

        for existing_key, existing_value in app_section.items():
            if existing_key not in ordered_app:
                ordered_app[existing_key] = existing_value
        on_disk["app"] = ordered_app
    except Exception as e:
        logger.warning(f"[Vars] Unable to apply defaults order to 'app' section: {e}")

    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(on_disk, f, indent=4)
            f.write("\n")
    except Exception as e:
        logger.error(f"[Vars] Failed to write config file: {e}")
        return False

    try:
        config["app"][key] = value
    except Exception:
        logger.debug("[Vars] In-memory config structure unexpected. Could not mirror update cleanly.")

    logger.debug(f"[Vars] Updated on-disk 'app.{key}' with '{value}'")
    return True

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
            logger.info(f"[Vars] Log file truncated: was {total_lines} lines, now {keep_lines} lines kept.")
        else:
            logger.info("[Vars] Log file is within the allowed size; no truncation performed.")
    except Exception as e:
        logger.error(f"[Vars] Error managing log file: {e}")

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
        parts.append(sanitize(part))

        # Commented out as downloading special episodes is not supported.
        # specials (Season 0) go in "/config["app"]["SPECIAL_EPISODES_FOLDER_NAME"]/..."
        # if int(season) == 0:
        #     norm = sanitize(part).lower()
        #     if norm in {
        #         "0", "00", # ${season}, ${seasonPadded}
        #         "s0", "s00", # S${season}, S${seasonPadded}
        #         "season 0", "season 00",  # "Season ${seasonPadded}"
        #     }:
        #         part = config["app"]["SPECIAL_EPISODES_FOLDER_NAME"]

    full_path = os.path.join(base_dir, *parts)

    # Add extension if the user omitted it
    if not full_path.lower().endswith(extension.lower()):
        full_path = f"{full_path}{extension}"

    logger.debug(f"[Vars] Built file path: {full_path}")

    return full_path

def get_episode_file_path(queue, series_id, season_key, episode_key, base_dir, extension=".mkv"):
    # Get data from the queue.
    raw_series = queue[series_id]["series"]["series_name"]
    season = queue[series_id]["seasons"][season_key]["season_number"]
    episode = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_number"]
    raw_episode_name = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_name"]

    # Treat specials (queue key starts with "S") as season 0 so the
    # build_folder_structure logic can detect them.
    if episode_key.startswith("S"):
        season = "0"

    # Build the folder structure and file name.
    file_name = build_folder_structure(base_dir, raw_series, season, episode, raw_episode_name, extension)

    logger.debug(f"[Vars] Built file path for series ID {series_id}, season {season_key}, episode {episode_key}: {file_name}")

    # Combine to form the full file path.
    return file_name

def iter_episodes(bucket_data: dict):
    if not isinstance(bucket_data, dict) or not bucket_data:
        return

    for series_id, series_info in bucket_data.items():
        seasons = series_info.get("seasons") or {}
        for season_key, season_info in seasons.items():
            episodes = season_info.get("episodes") or {}
            for episode_key, episode_info in episodes.items():
                yield series_id, season_key, episode_key, season_info, episode_info
