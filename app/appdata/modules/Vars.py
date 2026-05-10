import os
import re
import sys
import pwd
import grp
import json
import yaml
import tomllib
import subprocess
import unicodedata
from string import Template
from collections import OrderedDict
from pydantic import ValidationError

from .types.config import Config, AppConfig
from .types.service import Service, MdnxServices, ZloServices, Services
from .types.queue import Series, ServiceBucket


def _log(message: str, level: str = "info", exc_info=None) -> None:
    """Internal logging helper function. Needed to avoid circular imports."""

    try:
        from .Globals import log_manager
    except Exception:
        return

    try:
        match level:
            case "debug":
                log_manager.debug(message, exc_info=exc_info)
            case "warning":
                log_manager.warning(message, exc_info=exc_info)
            case "error":
                log_manager.error(message, exc_info=exc_info)
            case _:
                log_manager.info(message, exc_info=exc_info)
    except Exception:
        pass


def _resolve_config_path() -> str:
    """Determine the config file path to use, checking environment variable and default locations."""

    env_config_path = os.getenv("CONFIG_FILE")
    if env_config_path:
        return env_config_path

    default_config_paths = [
        "appdata/config/config.json",
        "appdata/config/config.yaml",
        "appdata/config/config.yml"
    ]

    for default_config_path in default_config_paths:
        if os.path.exists(default_config_path):
            _log(f"Found config file at {default_config_path}. Using it.", level="debug")
            return default_config_path

    return default_config_paths[0]


def _read_config(config_path: str) -> dict:
    """Read the config file from disk and return it as a dict."""

    config_extension = os.path.splitext(config_path)[1].lower()

    with open(config_path, "r", encoding="utf-8") as config_file:
        match config_extension:
            case ".json":
                loaded_config = json.load(config_file)
            case ".yaml" | ".yml":
                loaded_config = yaml.safe_load(config_file) or {}
            case _:
                raise ValueError(f"Unsupported config format: {config_path}. Use .json, .yaml, or .yml.")

    if not isinstance(loaded_config, dict):
        raise ValueError(f"Config root must be an object/mapping in {config_path}.")

    return loaded_config


def _write_config(config_path: str, config_data: dict) -> None:
    """Write the given config data dict to disk in the appropriate format based on file extension."""

    config_extension = os.path.splitext(config_path)[1].lower()

    with open(config_path, "w", encoding="utf-8") as config_file:
        match config_extension:
            case ".json":
                json.dump(config_data, config_file, indent=4, ensure_ascii=False)
                config_file.write("\n")
            case ".yaml" | ".yml":
                yaml.safe_dump(config_data, config_file, sort_keys=False, allow_unicode=True, indent=4)
            case _:
                raise ValueError(f"Unsupported config format: {config_path}. Use .json, .yaml, or .yml.")


def output_effective_config(config: Config, max_chunk: int = 8000):
    """Output the effective config to logs, ordered like the model defaults."""

    _log("Effective config:")

    config_dict = config.model_dump(by_alias=True)
    defaults_dict = Config().model_dump(by_alias=True)

    SKIP_ORDERING_KEYS = {
        "cr_monitor_series_id",
        "hidive_monitor_series_id",
        "adn_monitor_series_id",
        "zlo_cr_monitor_series_id",
        "zlo_hidive_monitor_series_id",
        "zlo_adn_monitor_series_id",
        "zlo_disneyplus_monitor_series_id",
        "zlo_amazon_monitor_series_id",
        "mdnx",
        "zlo"
    }

    def _order_like_defaults(config_node, defaults_node):
        if not isinstance(config_node, dict) or not isinstance(defaults_node, dict):
            return config_node

        ordered_node = OrderedDict()

        # defaults ordered keys go first
        for key in defaults_node.keys():
            if key in config_node:
                if key in SKIP_ORDERING_KEYS:
                    ordered_node[key] = config_node[key]
                else:
                    ordered_node[key] = _order_like_defaults(config_node[key], defaults_node.get(key))

        # then any remaining keys from config_node
        for key, value in config_node.items():
            if key not in ordered_node:
                if key in SKIP_ORDERING_KEYS:
                    ordered_node[key] = value
                else:
                    ordered_node[key] = _order_like_defaults(value, defaults_node.get(key))

        return ordered_node

    try:
        ordered_config = _order_like_defaults(config_dict, defaults_dict)
    except Exception as e:
        _log(f"Could not order config by defaults: {e}", level="warning")
        ordered_config = config_dict

    formatted_json = json.dumps(ordered_config, indent=4)

    for line in formatted_json.splitlines():
        for i in range(0, len(line), max_chunk):
            _log(line[i:i + max_chunk])


CONFIG_PATH = _resolve_config_path()
TZ = os.getenv("TZ", "America/New_York")

with open("pyproject.toml", "rb") as pyproject_file:
    APP_VERSION = str(tomllib.load(pyproject_file)["project"]["version"])


overrides = _read_config(CONFIG_PATH)

config = Config.model_validate(overrides)

del overrides

SERVICES = Services(
    mdnx=MdnxServices(
        crunchyroll=Service(
            service_name="crunchyroll",
            queue_bucket="Crunchyroll",
            display_name="Crunchyroll",
            tool="mdnx",
            config=config.mdnx,
            monitor_series_id=config.cr_monitor_series_id,
            monitor_config_key="cr_monitor_series_id",
            enabled=config.app.cr_enabled,
        ),
        hidive=Service(
            service_name="hidive",
            queue_bucket="HiDive",
            display_name="HiDive",
            tool="mdnx",
            config=config.mdnx,
            monitor_series_id=config.hidive_monitor_series_id,
            monitor_config_key="hidive_monitor_series_id",
            enabled=config.app.hidive_enabled,
        ),
        adn=Service(
            service_name="adn",
            queue_bucket="ADN",
            display_name="ADN",
            tool="mdnx",
            config=config.mdnx,
            monitor_series_id=config.adn_monitor_series_id,
            monitor_config_key="adn_monitor_series_id",
            enabled=config.app.adn_enabled,
        ),
    ),
    zlo=ZloServices(
        crunchyroll=Service(
            service_name="zlo-crunchyroll",
            queue_bucket="ZLO-Crunchyroll",
            display_name="ZLO Crunchyroll",
            tool="zlo",
            config=config.zlo.crunchyroll,
            monitor_series_id=config.zlo_cr_monitor_series_id,
            monitor_config_key="zlo_cr_monitor_series_id",
            enabled=config.app.zlo_cr_enabled,
        ),
        hidive=Service(
            service_name="zlo-hidive",
            queue_bucket="ZLO-HiDive",
            display_name="ZLO HiDive",
            tool="zlo",
            config=config.zlo.hidive,
            monitor_series_id=config.zlo_hidive_monitor_series_id,
            monitor_config_key="zlo_hidive_monitor_series_id",
            enabled=config.app.zlo_hidive_enabled,
        ),
        adn=Service(
            service_name="zlo-adn",
            queue_bucket="ZLO-ADN",
            display_name="ZLO ADN",
            tool="zlo",
            config=config.zlo.adn,
            monitor_series_id=config.zlo_adn_monitor_series_id,
            monitor_config_key="zlo_adn_monitor_series_id",
            enabled=config.app.zlo_adn_enabled,
        ),
        disney=Service(
            service_name="zlo-disney",
            queue_bucket="ZLO-DisneyPlus",
            display_name="ZLO DisneyPlus",
            tool="zlo",
            config=config.zlo.disneyplus,
            monitor_series_id=config.zlo_disneyplus_monitor_series_id,
            monitor_config_key="zlo_disneyplus_monitor_series_id",
            enabled=config.app.zlo_disneyplus_enabled,
        ),
        amazon=Service(
            service_name="zlo-amazon",
            queue_bucket="ZLO-Amazon",
            display_name="ZLO Amazon",
            tool="zlo",
            config=config.zlo.amazon,
            monitor_series_id=config.zlo_amazon_monitor_series_id,
            monitor_config_key="zlo_amazon_monitor_series_id",
            enabled=config.app.zlo_amazon_enabled,
        ),
    ),
)


# App settings
TEMP_DIR = config.app.temp_dir
BIN_DIR = config.app.bin_dir
LOG_DIR = config.app.log_dir
DATA_DIR = config.app.data_dir

# Regular expression to match invalid characters in filenames
INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

# Supported download tools
MDNX_ENABLED = False
for mdnx_service in SERVICES.mdnx.all():
    if mdnx_service.enabled:
        MDNX_ENABLED = True
        break

ZLO_ENABLED = False
for zlo_service in SERVICES.zlo.all():
    if zlo_service.enabled:
        ZLO_ENABLED = True
        break

# Vars related to media server stuff
PLEX_URL = config.app.plex_url
JELLY_URL = config.app.jelly_url
JELLY_API_KEY = config.app.jelly_api_key

PLEX_CONFIGURED = isinstance(PLEX_URL, str) and PLEX_URL.strip() != ""
JELLY_CONFIGURED = isinstance(JELLY_URL, str) and JELLY_URL.strip() != "" and isinstance(JELLY_API_KEY, str) and JELLY_API_KEY.strip() != ""

# This will look like: {"TEMP_DIR": "temp_dir", "CR_ENABLED": "cr_enabled", ...}
APP_ALIAS_KEY_TO_FIELD_NAME = {}
for field_name, field_info in AppConfig.model_fields.items():
    alias_key = field_info.alias or field_name
    APP_ALIAS_KEY_TO_FIELD_NAME[alias_key] = field_name

# This will look like: {"temp_dir": "TEMP_DIR", "cr_enabled": "CR_ENABLED", ...}
APP_FIELD_NAME_TO_ALIAS_KEY = {}
for field_name, field_info in AppConfig.model_fields.items():
    alias_key = field_info.alias or field_name
    APP_FIELD_NAME_TO_ALIAS_KEY[field_name] = alias_key

# This will look like: ["TEMP_DIR", "BIN_DIR", "LOG_DIR", ...]
APP_DEFAULT_KEY_ORDER = []
default_app_dict = AppConfig().model_dump(by_alias=True)
for alias_key in default_app_dict.keys():
    APP_DEFAULT_KEY_ORDER.append(alias_key)


def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log uncaught exceptions."""

    # skip logging for KeyboardInterrupt and SystemExit. Use the default handler.
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    _log("Uncaught exception", level="error", exc_info=(exc_type, exc_value, exc_traceback))

    # call the default excepthook as well
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def dedupe_preserve_order(items, key=None):
    """
    Deduplicate a list while preserving order.
    If 'key' is provided, it is used to normalize items for comparison.
    """

    if not items:
        return []

    seen_keys = set()
    result = []

    if key is None:
        for item in items:
            if item not in seen_keys:
                seen_keys.add(item)
                result.append(item)
        return result

    for item in items:
        normalized = key(item)
        if normalized not in seen_keys:
            seen_keys.add(normalized)
            result.append(item)
    return result


def dedupe_casefold(items):
    """Deduplicate a list of strings in a case-insensitive manner while preserving order."""

    return dedupe_preserve_order(items, key=lambda s: s.casefold())


def format_duration(seconds: int) -> str:
    """Format a duration in seconds into a human-readable string."""

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


def check_widevine(service_path: str) -> bool:
    if not os.path.isdir(service_path):
        return False

    service_folder_contents = []
    for name in os.listdir(service_path):
        if name == ".gitkeep":
            continue
        service_folder_contents.append(name)

    has_files = False
    for name in service_folder_contents:
        full = os.path.join(service_path, name)
        if os.path.isfile(full):
            has_files = True
            break

    if not has_files:
        return False

    found_wvd = False
    found_bin = False
    found_pem = False
    found_device_client_id_blob = False
    found_device_private_key = False

    for name in service_folder_contents:
        full = os.path.join(service_path, name)
        if not os.path.isfile(full):
            continue

        lower = name.lower()

        if lower.endswith(".wvd"):
            found_wvd = True
            break

        if lower.endswith(".bin"):
            found_bin = True

        if lower.endswith(".pem"):
            found_pem = True

        if lower == "device_client_id_blob":
            found_device_client_id_blob = True

        if lower == "device_private_key":
            found_device_private_key = True

    if found_wvd:
        return True

    if found_bin and found_pem:
        return True

    if found_device_client_id_blob and found_device_private_key:
        return True

    return False


def check_playready(service_path: str) -> bool:
    if not os.path.isdir(service_path):
        return False

    service_folder_contents = []
    for name in os.listdir(service_path):
        if name == ".gitkeep":
            continue
        service_folder_contents.append(name)

    has_files = False
    for name in service_folder_contents:
        full = os.path.join(service_path, name)
        if os.path.isfile(full):
            has_files = True
            break

    if not has_files:
        return False

    found_prd = False
    bgroupcert_path = None
    zgpriv_path = None

    for name in service_folder_contents:
        full = os.path.join(service_path, name)
        if not os.path.isfile(full):
            continue

        lower = name.lower()

        if lower.endswith(".prd"):
            found_prd = True
            break

        if lower == "bgroupcert.dat":
            bgroupcert_path = full

        if lower == "zgpriv.dat":
            zgpriv_path = full

    if found_prd:
        return True

    if bgroupcert_path and zgpriv_path:
        bgroupcert_size = os.path.getsize(bgroupcert_path)
        zgpriv_size = os.path.getsize(zgpriv_path)

        if bgroupcert_size >= 1024 and zgpriv_size == 32:
            return True

    return False


def validate_cdm(service_path: str, service_name: str, required: bool = False) -> bool:
    match service_name:
        case "Widevine":
            is_valid = check_widevine(service_path)
        case "PlayReady":
            is_valid = check_playready(service_path)
        case _:
            _log(f"Unknown CDM type: {service_name}", level="critical")
            sys.exit(1)

    if is_valid:
        _log(f"{service_name} CDM is valid at path: {service_path}")
        return True

    if required:
        _log(f"{service_name} CDM is required but was not found or is invalid at path: {service_path}", level="critical")
        sys.exit(1)

    return False


def _ffprobe(file_path: str) -> list[dict]:
    """Run ffprobe -show_streams and return the parsed list of stream dicts."""

    timeout = 180
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path]

    _log(f"Running ffprobe on {file_path} with command: {' '.join(cmd)}", level="debug")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _log(f"ffprobe timed out after {format_duration(timeout)} on {file_path}", level="error")
        return []

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as decode_error:
        _log(f"ffprobe JSON decode error on {file_path}: {decode_error}", level="error")
        return []

    if data == {}:
        _log(f"ffprobe found no streams for {file_path}", level="error")
        return []

    streams = data.get("streams") or []
    if not isinstance(streams, list):
        _log(f"ffprobe returned non-list streams for {file_path}", level="error")
        return []

    _log(f"ffprobe output for {file_path}: {streams}", level="debug")

    return streams


def get_season_monitor_config(service: str, series_id: str, season_id: str | None):
    """Get the monitor config for a specific series season."""

    if not season_id:
        return None

    normalized_service = service.strip().lower()

    service_obj = SERVICES.get(normalized_service)
    if service_obj is None:
        _log(f"Unknown service '{service}' when reading season monitor config.", level="error")
        return None

    service_monitor_config = service_obj.monitor_series_id

    series_config = service_monitor_config.get(series_id)
    if not series_config:
        return None

    return series_config.get(season_id)


def apply_series_blacklist(tmp_dict: dict[str, Series], service: str) -> dict[str, Series]:
    """Apply per-season blacklists from config: mark matching episodes as episode_skip=True."""

    for series_id, series in tmp_dict.items():
        for _season_key, season in series.seasons.items():
            season_monitor = get_season_monitor_config(service, series_id, season.season_id)
            if season_monitor is None:
                continue

            blacklist_rules = season_monitor.blacklists
            if blacklist_rules is None:
                continue

            if "*" in blacklist_rules:
                for episode in season.episodes.values():
                    episode.episode_skip = True
                continue

            for episode_key, episode in season.episodes.items():
                try:
                    local_episode_number = int(episode_key.lstrip("E"))
                except Exception:
                    continue

                should_skip_episode = False
                for raw_rule in blacklist_rules:
                    if raw_rule is None:
                        continue
                    rule_text = raw_rule.strip()
                    if not rule_text:
                        continue

                    if "-" in rule_text:
                        parts = rule_text.split("-", 1)
                        try:
                            range_start = int(parts[0])
                            range_end = int(parts[1])
                        except Exception:
                            continue
                        if range_start > range_end:
                            range_start, range_end = range_end, range_start
                        if range_start <= local_episode_number <= range_end:
                            should_skip_episode = True
                            break
                    else:
                        try:
                            single_episode_number = int(rule_text)
                        except Exception:
                            continue
                        if local_episode_number == single_episode_number:
                            should_skip_episode = True
                            break

                if should_skip_episode:
                    episode.episode_skip = True

    return tmp_dict


def sanitize(path_segment: str, ascii_only: bool = False, max_len: int = 255) -> str:
    """
    Sanitize a path segment (file or folder name) by:
      - Unicode normalize (NFKC) and map smart punctuation
      - Remove control chars and filesystem-illegal chars
      - Drop most Unicode symbols (e.g., ♪) -> space
      - Replace "_" with space, collapse whitespace, trim
      - Tighten spaces only around the extension dot
      - Avoid Windows trailing dot/space and reserved names
      - Optionally force ASCII only
      - Truncate to max_len, preserving extension when possible
    """
    original_segment = path_segment

    # normalize then translate common unicode punctuation to ASCII
    normalized = unicodedata.normalize("NFKC", path_segment)
    punctuation_translation = {
        ord('“'): '"', ord('”'): '"', ord('„'): '"', ord('‟'): '"',
        ord('’'): "'", ord('‘'): "'", ord('‚'): "'", ord('ʼ'): "'",  # noqa: RUF001
        ord('–'): '-', ord('—'): '-', ord('-'): '-',  # non-breaking hyphen maps to hyphen  # noqa: RUF001
        ord('…'): '...', ord('•'): '-', ord('·'): '-', ord('‧'): '-',
        ord('／'): '/', ord('＼'): '\\', ord('～'): '~',  # noqa: RUF001
        ord('：'): ':', ord('；'): ';', ord('！'): '!', ord('？'): '?',  # noqa: RUF001
    }
    sanitized = normalized.translate(punctuation_translation)
    sanitized = INVALID_CHARS_RE.sub(" ", sanitized)

    # remove other control chars: DEL (0x7F) and C1 controls (0x80-0x9F)
    sanitized = re.sub(r"[\x7F-\x9F]", " ", sanitized)

    # drop most Unicode symbols (So/Sm/Sk) and any remaining "Other" categories
    def _drop_symbols(text: str) -> str:
        builder = []
        for ch in text:
            category = unicodedata.category(ch)
            if category.startswith("C") or category in ("So", "Sm", "Sk"):
                builder.append(" ")
            else:
                builder.append(ch)
        return "".join(builder)

    sanitized = _drop_symbols(sanitized)

    # underscores -> spaces
    sanitized = sanitized.replace("_", " ")

    # collapse whitespace and trim ends
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    # remove spaces before the final extension dot
    sanitized = re.sub(r"\s+(\.[A-Za-z0-9]{1,10})$", r"\1", sanitized)

    # remove spaces after the final extension dot
    sanitized = re.sub(r"\.(\s+)([A-Za-z0-9]{1,10})$", r".\2", sanitized)

    # trim trailing spaces/dots from the segment
    sanitized = sanitized.rstrip(" .")

    # optional strict ASCII mode
    if ascii_only:
        sanitized = unicodedata.normalize("NFKD", sanitized).encode("ascii", "ignore").decode("ascii")
        sanitized = re.sub(r"[^A-Za-z0-9 .()\-[\]{}!@#$%^&+=,;'%~`-]", " ", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        sanitized = re.sub(r"\s+(\.[A-Za-z0-9]{1,10})$", r"\1", sanitized)
        sanitized = re.sub(r"\.(\s+)([A-Za-z0-9]{1,10})$", r".\2", sanitized)
        sanitized = sanitized.rstrip(" .")

    # truncate safely, preserving extension if present
    if len(sanitized) > max_len:
        if "." in sanitized:
            name_part, dot, ext_part = sanitized.rpartition(".")
            base = name_part[: max(1, max_len - len(ext_part) - 1)]
            sanitized = f"{base}{dot}{ext_part}".rstrip(" .")
        else:
            sanitized = sanitized[:max_len].rstrip(" .")

    if sanitized != original_segment:
        _log(f"Sanitized {original_segment!r} to {sanitized!r}", level="debug")

    return sanitized


def get_running_user():
    """Get the current running user and group information (linux only)."""

    uid = os.getuid()    # real UID
    gid = os.getgid()    # real GID
    euid = os.geteuid()  # effective UID (after set-uid, if any)
    egid = os.getegid()  # effective GID

    user = pwd.getpwuid(uid).pw_name
    group = grp.getgrgid(gid).gr_name

    _log(f"Running as UID={uid} ({user}), GID={gid} ({group})")
    _log(f"Effective UID={euid}, effective GID={egid}")

    return (uid, user, gid, group, euid, egid)


def update_app_config(config_key: str, new_value) -> bool:
    """
    Update one AppConfig option in config.json/yaml/yml under the 'app' section.

    config_key can be either:
      - field name: "cr_force_reauth"
      - alias key:  "CR_FORCE_REAUTH"
    """

    global config

    # resolve to alias key to write to disk
    if config_key in APP_FIELD_NAME_TO_ALIAS_KEY:
        alias_key_to_write = APP_FIELD_NAME_TO_ALIAS_KEY[config_key]
    elif config_key in APP_ALIAS_KEY_TO_FIELD_NAME:
        alias_key_to_write = config_key
    else:
        _log(f"Unknown app config key: {config_key}", level="error")
        return False

    # read config file from disk
    try:
        on_disk_config = _read_config(CONFIG_PATH)
    except Exception as read_error:
        _log(f"Failed to read config file: {read_error}", level="error")
        return False

    app_config_section = on_disk_config.get("app")
    if not isinstance(app_config_section, dict):
        _log("Invalid config: missing 'app' object.", level="error")
        return False

    # apply update
    app_config_section[alias_key_to_write] = new_value

    # validate updated app section before writing
    try:
        AppConfig.model_validate(app_config_section)
    except ValidationError as validation_error:
        _log(f"Invalid value for app.{alias_key_to_write}: {validation_error}", level="error")
        return False

    # write back to disk config.json/yaml/yml
    try:
        _write_config(CONFIG_PATH, on_disk_config)
    except Exception as write_error:
        _log(f"Failed to write config file: {write_error}", level="error")
        return False

    # refresh in-memory app config
    try:
        config.app = AppConfig.model_validate(app_config_section)
    except ValidationError as refresh_error:
        _log(f"Wrote config, but failed to refresh in-memory app config: {refresh_error}", level="warning")

    _log(f"Updated on-disk 'app.{alias_key_to_write}' with '{new_value}'", level="debug")
    return True


def build_folder_structure(base_dir: str, series_title: str, season: str, episode: str, episode_name: str, extension: str = ".mkv") -> str:
    """Build the folder structure and file name based on the template in config."""

    template_str = config.app.folder_structure

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
        # specials (Season 0) go in "config["app"]["SPECIAL_EPISODES_FOLDER_NAME"]..."
        # if int(season) == 0:
        #     norm = sanitize(part).lower()
        #     if norm in {
        #         "0", "00", # ${season}, ${seasonPadded}
        #         "s0", "s00", # S${season}, S${seasonPadded}
        #         "season 0", "season 00",  # "Season ${seasonPadded}"
        #     }:
        #         part = config["app"]["SPECIAL_EPISODES_FOLDER_NAME"]

    full_path = os.path.join(base_dir, *parts)

    # add extension if the user omitted it
    if not full_path.lower().endswith(extension.lower()):
        full_path = f"{full_path}{extension}"

    _log(f"Built file path: {full_path}", level="debug")

    return full_path


def get_episode_file_path(bucket: ServiceBucket, series_id: str, season_key: str, episode_key: str, base_dir: str, extension: str = ".mkv") -> str:
    """Build the on-disk file path for one queued episode using the configured folder structure."""

    series = bucket.series[series_id]
    season = series.seasons[season_key]
    episode = season.episodes[episode_key]

    raw_series = series.series.series_name
    season_number = season.season_number
    episode_number = episode.episode_number
    raw_episode_name = episode.episode_name

    if episode_key.startswith("S"):
        season_number = "0"

    file_name = build_folder_structure(base_dir, raw_series, season_number, episode_number, raw_episode_name, extension)

    _log(f"Built file path for series ID {series_id}, season {season_key}, episode {episode_key}: {file_name}", level="debug")

    return file_name


def iter_episodes(bucket: ServiceBucket):
    """Yield (series_id, season_key, episode_key, Season, Episode) tuples for every episode in the bucket."""

    if bucket is None:
        return

    for series_id, series in bucket.series.items():
        for season_key, season in series.seasons.items():
            for episode_key, episode in season.episodes.items():
                yield series_id, season_key, episode_key, season, episode
