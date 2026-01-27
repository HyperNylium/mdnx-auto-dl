import os
import re
import sys
import pwd
import grp
import json
import subprocess
import unicodedata
from string import Template
from collections import OrderedDict


CONFIG_PATH = os.getenv("CONFIG_FILE", "appdata/config/config.json")
QUEUE_PATH = os.getenv("QUEUE_FILE", "appdata/config/queue.json")
TZ = os.getenv("TZ", "America/New_York")


def _log(message: str, level: str = "info", exc_info=None) -> None:
    """Internal logging helper function. Needed to avoid circular imports."""

    try:
        from .Globals import log_manager
    except Exception:
        return

    try:
        if level == "debug":
            log_manager.debug(message, exc_info=exc_info)
        elif level == "warning":
            log_manager.warning(message, exc_info=exc_info)
        elif level == "error":
            log_manager.error(message, exc_info=exc_info)
        else:
            log_manager.info(message, exc_info=exc_info)
    except Exception:
        pass


def merge_config(defaults: dict, overrides: dict) -> dict:
    """
    Recursively merge two configuration dicts.
    Values from 'overrides' take precedence over 'defaults'.
    If a value in 'overrides' is None, the corresponding value from 'defaults' is retained.
    """

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


def output_effective_config(config, default_config, max_chunk=8000):
    """Output the effective config to logs, ordered like the defaults."""

    _log("Effective config: ")
    try:
        SKIP_ORDERING_KEYS = {"cr_monitor_series_id", "hidive_monitor_series_id", "mdnx"}

        def _order_like_defaults(config_node: dict, defaults_node: dict):
            if not isinstance(config_node, dict):
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

        ordered_config = _order_like_defaults(config, default_config)
    except Exception as e:
        _log(f"Could not order config by defaults: {e}", level="debug")
        ordered_config = config  # fall back without reordering

    formatted_json = json.dumps(ordered_config, indent=4)
    for line in formatted_json.splitlines():
        for i in range(0, len(line), max_chunk):
            _log(line[i:i + max_chunk])


# every default config value
CONFIG_DEFAULTS = {
    "cr_monitor_series_id": {},
    "hidive_monitor_series_id": {},
    "app": {
        "TEMP_DIR": "/app/appdata/temp",
        "BIN_DIR": "/app/appdata/bin",
        "LOG_DIR": "/app/appdata/logs",
        "DATA_DIR": "/data",
        "CR_ENABLED": False,
        "CR_USERNAME": "",
        "CR_PASSWORD": "",
        "HIDIVE_ENABLED": False,
        "HIDIVE_USERNAME": "",
        "HIDIVE_PASSWORD": "",
        "BACKUP_DUBS": ["zho"],
        "FOLDER_STRUCTURE": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}",
        "CHECK_MISSING_DUB_SUB": True,
        "CHECK_FOR_UPDATES_INTERVAL": 3600,
        "EPISODE_DL_DELAY": 30,
        "CR_FORCE_REAUTH": False,
        "CR_SKIP_API_TEST": False,
        "HIDIVE_FORCE_REAUTH": False,
        "HIDIVE_SKIP_API_TEST": False,
        "ONLY_CREATE_QUEUE": False,
        "SKIP_QUEUE_REFRESH": False,
        "DRY_RUN": False,
        "LOG_LEVEL": "info",
        "MAX_LOG_ARCHIVES": 5,
        "NOTIFICATION_PREFERENCE": "none",
        "NTFY_SCRIPT_PATH": "/app/appdata/config/ntfy.sh",
        "SMTP_FROM": "",
        "SMTP_TO": "",
        "SMTP_HOST": "",
        "SMTP_USERNAME": "",
        "SMTP_PASSWORD": "",
        "SMTP_PORT": 587,
        "SMTP_STARTTLS": True,
        "PLEX_URL": None,
        "PLEX_TOKEN": None,
        "PLEX_URL_OVERRIDE": False,
        "JELLY_URL": None,
        "JELLY_API_KEY": None,
        "JELLY_URL_OVERRIDE": False
    },
    "mdnx": {
        "bin-path": {
            "ffmpeg": "ffmpeg",
            "ffprobe": "ffprobe",
            "mkvmerge": "mkvmerge",
            "mp4decrypt": "/app/appdata/bin/Bento4-SDK/mp4decrypt"
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

# load the config file
with open(CONFIG_PATH, 'r') as config_file:
    LOCAL_CONFIG = json.load(config_file)

config = merge_config(defaults=CONFIG_DEFAULTS, overrides=LOCAL_CONFIG)

del LOCAL_CONFIG

# App settings
TEMP_DIR = config["app"]["TEMP_DIR"]
BIN_DIR = config["app"]["BIN_DIR"]
LOG_DIR = config["app"]["LOG_DIR"]
DATA_DIR = config["app"]["DATA_DIR"]

# MDNX config settings
MDNX_CONFIG = config["mdnx"]

# Dynamic paths
MDNX_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "mdnx", "aniDL")
MDNX_SERVICE_CR_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "cr_token.yml")
MDNX_SERVICE_HIDIVE_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "hd_new_token.yml")

# Regular expression to match invalid characters in filenames
INVALID_CHARS_RE = re.compile(r'[<>:"/\\|?*\x00-\x1F]')

# Streaming services enabled
MDNX_CR_ENABLED: bool = config["app"]["CR_ENABLED"]
MDNX_HIDIVE_ENABLED: bool = config["app"]["HIDIVE_ENABLED"]

# Vars related to media server stuff
PLEX_URL = config["app"]["PLEX_URL"]
JELLY_URL = config["app"]["JELLY_URL"]
JELLY_API_KEY = config["app"]["JELLY_API_KEY"]

PLEX_CONFIGURED = isinstance(PLEX_URL, str) and PLEX_URL.strip() != ""
JELLY_CONFIGURED = isinstance(JELLY_URL, str) and JELLY_URL.strip() != "" and isinstance(JELLY_API_KEY, str) and JELLY_API_KEY.strip() != ""

# Strings in multi-downloader-nx's logs that indicate a successful download
MDNX_API_OK_LOGS = [
    "[mkvmerge Done]",
    "[mkvmerge] Mkvmerge finished"
]

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
    NAME_TO_CODE[name] = vals[0]  # vals[0] is the code

# This will look like: {"en", "es-419", ...}
VALID_LOCALES = set()
for vals in LANG_MAP.values():
    VALID_LOCALES.add(vals[1])  # vals[1] is the locale

# This will look like: {"eng": "en", "spa": "es-419", ...}
CODE_TO_LOCALE = {}
for _name, vals in LANG_MAP.items():
    code = vals[0].lower()
    loc = vals[1].lower()
    CODE_TO_LOCALE[code] = loc


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

    return dedupe_preserve_order(items, key=lambda s: (s or "").casefold())


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


def select_dubs(episode_info: dict):
    """Determine which dubs to download based on desired, backup, and available dubs."""

    desired_dubs = set()
    for lang in config["mdnx"]["cli-defaults"]["dubLang"]:
        desired_dubs.add(lang)

    backup_dubs = set()
    for lang in config["app"]["BACKUP_DUBS"]:
        backup_dubs.add(lang)

    available_dubs = set()
    for dub in episode_info["available_dubs"]:
        available_dubs.add(dub)

    _log(f"Desired dubs: {desired_dubs}", level="debug")
    _log(f"Backup dubs: {backup_dubs}", level="debug")
    _log(f"Available dubs: {available_dubs}", level="debug")

    # if desired dub is available, use the default already present.
    if desired_dubs & available_dubs:
        _log(f"Desired dubs available: {desired_dubs & available_dubs}", level="debug")
        return None

    # if backups are available but not the desired dubs, override with that intersection.
    if backup_dubs & available_dubs:
        _log(f"Desired dubs not available, but backup dubs are: {backup_dubs & available_dubs}", level="debug")
        return list(backup_dubs & available_dubs)

    # otherwise fall back to the alphabetically first available dub.
    if available_dubs:
        _log("Neither desired nor backup dubs are available. Falling back to first available dub.", level="debug")
        first_dub = next(iter(sorted(available_dubs)))
        return [first_dub]

    # no dubs at all, which is unexpected tbh.
    # but, you never know with Crunchyroll...
    # will skip the episode in this case.
    _log("No dubs available at all for this episode. Skipping it.", level="debug")
    return False


def probe_streams(file_path: str) -> tuple[set, set]:
    """Use ffprobe to get audio and subtitle languages from the given media file."""

    timeout = 180  # 3 minutes
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path]

    _log(f"Running ffprobe on {file_path} with command: {' '.join(cmd)}", level="debug")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _log(f"ffprobe timed out after {format_duration(timeout)} on {file_path}", level="error")
        return set(), set()

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        _log(f"ffprobe JSON decode error on {file_path}: {e}", level="error")
        return set(), set()

    if data == {}:  # no streams found
        _log(f"ffprobe found no dubs/subs for {file_path}", level="error")
        return set(), set()

    _log(f"ffprobe output for {file_path}: {data}", level="debug")

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

    _log(f"Probed {file_path}: audio languages: {audio_langs}, subtitle languages: {sub_langs}", level="debug")

    return audio_langs, sub_langs


def apply_series_blacklist(tmp_dict: dict, monitor_series_config: dict, service: str) -> dict:
    """Apply series/season/episode blacklists from config to the given tmp_dict structure."""

    if not isinstance(monitor_series_config, dict):
        _log(f"{service}_monitor_series_id must be a dict.", level="error")
        monitor_series_config = {}

    # rules are strings like "S:<season_id>", "S:<season_id>:E:<index>", or "S:<season_id>:E:<start>-<end>"
    def parse_blacklist_rules(rules):
        blacklisted_season_ids = set()
        # season_id -> list of rules; each rule is int (single ep) or (start, end) tuple
        episode_blacklist_rules = {}
        if not rules:
            return blacklisted_season_ids, episode_blacklist_rules

        if isinstance(rules, str):
            if not rules.strip():  # empty string means no blacklist
                return blacklisted_season_ids, episode_blacklist_rules
            rules = [rules]

        for raw_rule in rules:
            if not raw_rule:
                continue
            rule_text = str(raw_rule).strip()
            match = re.fullmatch(r"S:([^:]+)(?::E:(\d+)(?:-(\d+))?)?", rule_text)
            if not match:
                continue

            season_id_str = match.group(1)
            start_str = match.group(2)
            end_str = match.group(3)

            if start_str is None:
                # whole season blacklist
                blacklisted_season_ids.add(season_id_str)
            else:
                rules_for_season = episode_blacklist_rules.setdefault(season_id_str, [])
                if end_str is None:
                    # single episode
                    rules_for_season.append(int(start_str))
                else:
                    # episode range
                    start_idx, end_idx = int(start_str), int(end_str)
                    if start_idx > end_idx:
                        start_idx = end_idx
                        end_idx = start_idx
                    rules_for_season.append((start_idx, end_idx))

        return blacklisted_season_ids, episode_blacklist_rules

    for series_id, series_info in (tmp_dict or {}).items():
        rules_value = monitor_series_config.get(series_id)
        if rules_value is None:
            continue

        blacklisted_season_ids, episode_blacklist_rules = parse_blacklist_rules(rules_value)
        if not blacklisted_season_ids and not episode_blacklist_rules:
            continue

        for _season_key, season_info in (series_info.get("seasons") or {}).items():
            season_id = season_info.get("season_id")
            if not season_id:
                continue

            # season-level blacklist
            if season_id in blacklisted_season_ids:
                for episode_info in (season_info.get("episodes") or {}).values():
                    episode_info["episode_skip"] = True
                continue

            # episode-level blacklist for this season_id
            rules_for_season = episode_blacklist_rules.get(season_id)
            if rules_for_season:
                for episode_key, episode_info in (season_info.get("episodes") or {}).items():
                    try:
                        episode_index = int(str(episode_key).lstrip("E"))
                    except Exception:
                        continue

                    for rule in rules_for_season:
                        if isinstance(rule, tuple):
                            if rule[0] <= episode_index <= rule[1]:
                                episode_info["episode_skip"] = True
                                break
                        else:
                            if episode_index == rule:
                                episode_info["episode_skip"] = True
                                break

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

        # format each element in the list. If an element is a string, wrap it in quotes.
        formatted_elements = []

        for item in val:
            if isinstance(item, str):
                formatted_elements.append(f"\"{item}\"")
            else:
                formatted_elements.append(str(item))

        formatted_elements = ", ".join(formatted_elements)
        return f'[{formatted_elements}]'

    else:
        return f'"{val}"'


def update_mdnx_config():
    """Update MDNX config files based on current settings in config.json."""

    _log("Updating MDNX config files with new settings from config.json...")

    for mdnx_config_file, mdnx_config_settings in MDNX_CONFIG.items():
        file_path = os.path.join(BIN_DIR, "mdnx", "config", f"{mdnx_config_file}.yml")

        lines = []
        for setting_key, setting_value in mdnx_config_settings.items():
            formatted_value = format_value(setting_value)
            line = f"{setting_key}: {formatted_value}\n"
            lines.append(line)

        with open(file_path, "w") as file:
            file.writelines(lines)

        _log(f"Updated {file_path} with new settings.", level="debug")

    _log("MDNX config updated.")


def update_app_config(key: str, value):
    """Update a single key-value pair in the on-disk config.json file under the 'app' section."""

    global config

    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            on_disk = json.load(f, object_pairs_hook=OrderedDict)
    except Exception as e:
        _log(f"Failed to read config file: {e}", level="error")
        return False

    app_section = on_disk.get("app")
    if not isinstance(app_section, dict):
        _log("Invalid config: missing 'app' object.", level="error")
        return False

    app_section[key] = value

    # reorder "app" section according to CONFIG_DEFAULTS["app"] key order.
    # keys not present in defaults are appended in their current relative order.
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
        _log(f"Unable to apply defaults order to 'app' section: {e}", level="warning")

    try:
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(on_disk, f, indent=4)
            f.write("\n")
    except Exception as e:
        _log(f"Failed to write config file: {e}", level="error")
        return False

    try:
        config["app"][key] = value
    except Exception:
        _log("In-memory config structure unexpected. Could not mirror update cleanly.", level="debug")

    _log(f"Updated on-disk 'app.{key}' with '{value}'", level="debug")
    return True


def build_folder_structure(base_dir: str, series_title: str, season: str, episode: str, episode_name: str, extension: str = ".mkv") -> str:
    """Build the folder structure and file name based on the template in config."""

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

    # add extension if the user omitted it
    if not full_path.lower().endswith(extension.lower()):
        full_path = f"{full_path}{extension}"

    _log(f"Built file path: {full_path}", level="debug")

    return full_path


def get_episode_file_path(queue, series_id, season_key, episode_key, base_dir, extension=".mkv"):
    """Get the full file path for the given series/season/episode from the queue."""

    # get data from the queue.
    raw_series = queue[series_id]["series"]["series_name"]
    season = queue[series_id]["seasons"][season_key]["season_number"]
    episode = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_number"]
    raw_episode_name = queue[series_id]["seasons"][season_key]["episodes"][episode_key]["episode_name"]

    # treat specials (queue key starts with "S") as season 0 so the
    # build_folder_structure logic can detect them.
    if episode_key.startswith("S"):
        season = "0"

    # build the folder structure and file name.
    file_name = build_folder_structure(base_dir, raw_series, season, episode, raw_episode_name, extension)

    _log(f"Built file path for series ID {series_id}, season {season_key}, episode {episode_key}: {file_name}", level="debug")

    # combine to form the full file path.
    return file_name


def iter_episodes(bucket_data: dict):
    """
    Generator to iterate over all episodes in the given bucket_data structure.
    Yields tuples of (series_id, season_key, episode_key, season_info, episode_info).
    """

    if not isinstance(bucket_data, dict) or not bucket_data:
        return

    for series_id, series_info in bucket_data.items():
        seasons = series_info.get("seasons") or {}
        for season_key, season_info in seasons.items():
            episodes = season_info.get("episodes") or {}
            for episode_key, episode_info in episodes.items():
                yield series_id, season_key, episode_key, season_info, episode_info
