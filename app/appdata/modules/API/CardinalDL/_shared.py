import os
import re
import json
import sqlite3

from appdata.modules.Vars import (
    config,
    BIN_DIR,
    dedupe_casefold, ffprobe
)
from appdata.modules.types.queue import Episode
from appdata.modules.types.service import Service


# format is: "Language Name": (cdl_code, iso_639_2_code or None)
LANG_MAP: dict[str, tuple[str, str | None]] = {
    "English": ("EN", "eng"),
    "English (India)": ("EN-IN", None),
    "English (UK)": ("EN-GB", None),

    "Spanish": ("LA-ES", "spa"),
    "Spanish (Mexico)": ("MX-ES", None),
    "Castilian": ("ES", None),

    "Portuguese": ("PT", "por"),
    "Portuguese (Portugal)": ("PT-PT", None),

    "French":  ("FR", "fra"),
    "French (Canada)": ("FR-CA", None),

    "German": ("DE", "deu"),

    "Arabic": ("AR", "ara"),
    "Arabic (Saudi Arabia)": ("AR", None),
    "Arabic (Modern Standard)": ("AR-001", None),

    "Italian": ("IT", "ita"),
    "Russian": ("RU", "rus"),
    "Turkish": ("TR", "tur"),
    "Hindi": ("HI", "hin"),

    "Chinese (Mandarin, PRC)": ("CN", "zho"),
    "Chinese (Mainland China)": ("CN", None),
    "Chinese": ("CN", None),
    "Chinese (Taiwan)": ("TW", None),
    "Chinese (Traditional)": ("TW", None),
    "TraditionalChinese": ("TW", None),
    "Chinese (Hong-Kong)": ("HK", None),
    "Cantonese": ("HK", None),
    "Chinese (Simplified)": ("CN", None),
    "SimplifiedChinese": ("CN", None),

    "Korean": ("KO", "kor"),
    "Catalan": ("CA", "cat"),
    "Polish": ("PL", "pol"),
    "Thai": ("TH", "tha"),
    "Tamil (India)": ("TA", "tam"),
    "Malay (Malaysia)": ("MS", "msa"),
    "Vietnamese": ("VI", "vie"),
    "Indonesian": ("ID", "ind"),
    "Telugu (India)": ("TE", "tel"),
    "Japanese": ("JP", "jpn"),

    "Norwegian Bokmal": ("NB", "nob"),

    "Dutch": ("NL", "nld"),
    "Swedish": ("SV", "swe"),
    "Finnish": ("FI", "fin"),
    "Norwegian": ("NO", "nor"),
    "Danish": ("DA", "dan"),
    "Greek": ("EL", "ell"),
    "Hebrew": ("HE", "heb"),
    "Ukrainian": ("UK", "ukr"),
    "Persian": ("FA", "fas"),
    "Bengali": ("BN", "ben"),
    "Czech": ("CS", "ces"),
    "Romanian": ("RO", "ron"),
    "Hungarian": ("HU", "hun"),
    "Tagalog": ("TL", "tgl"),
    "Khmer": ("KM", "khm"),
    "Burmese": ("MY", "mya"),
    "Mongolian": ("MN", "mon"),
    "Icelandic": ("IS", "isl"),
    "Slovak": ("SK", "slk"),
    "Kannada": ("KN", "kan"),
    "Malayalam": ("ML", "mal"),
    "Basque":  ("EU", "eus"),
    "Galician": ("GL", "glg"),
    "Serbian": ("SR", "srp"),
    "Macedonian": ("MK", "mkd"),
    "Croatian": ("HR", "hrv"),
    "Slovenian": ("SL", "slv"),
    "Bulgarian": ("BG", "bul"),
    "Latvian": ("LV", "lav"),
    "Lithuanian": ("LT", "lit"),
    "Estonian": ("ET", "est")
}


# ISO 639-2/B to 639-2/T map
ISO_B_TO_T: dict[str, str] = {
    "fre": LANG_MAP["French"][1],
    "ger": LANG_MAP["German"][1],
    "chi": LANG_MAP["Chinese (Mandarin, PRC)"][1],
    "cze": LANG_MAP["Czech"][1],
    "dut": LANG_MAP["Dutch"][1],
    "gre": LANG_MAP["Greek"][1],
    "per": LANG_MAP["Persian"][1],
    "slo": LANG_MAP["Slovak"][1],
    "bur": LANG_MAP["Burmese"][1],
    "ice": LANG_MAP["Icelandic"][1],
    "mac": LANG_MAP["Macedonian"][1],
    "rum": LANG_MAP["Romanian"][1],
    "baq": LANG_MAP["Basque"][1],
    "may": LANG_MAP["Malay (Malaysia)"][1]
}


# "dv" covers all Dolby Vision variants
DV_VIDEO_RANGES = {"dv", "dv-hdr10", "dv-hdr10+"}

_CDL_DEFAULTS: dict[str, tuple[list[str], list[str]]] = {}
CDL_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "cardinaldl", "cardinaldl")

VALID_CDL_CODES: set[str] = {cdl_code for cdl_code, _ in LANG_MAP.values()}


def check_cdl_signed_in(storage_path: str) -> tuple[bool, str]:
    """Check a CardinalDL storage DB exists and the user has signed in with the correct provider."""

    if not os.path.isfile(storage_path):
        return (False, f"CardinalDL storage database was not found at: {storage_path}\nPlease mount the correct CardinalDL storage folder and restart the application.")

    try:
        connection = sqlite3.connect(storage_path)
        try:
            rows = connection.execute(
                "SELECT key, value FROM kv_store WHERE key IN ('account', 'accountDeviceId', 'accountDeviceProofKeyV2')"
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.Error as db_error:
        return (False, f"Could not read the CardinalDL storage database at {storage_path}: {db_error}")

    stored_values = {}
    for stored_key, stored_value in rows:
        if stored_value is not None:
            stored_values[stored_key] = stored_value

    for required_key in ("account", "accountDeviceId", "accountDeviceProofKeyV2"):
        if required_key not in stored_values:
            return (False, f"You are not signed into CardinalDL. The storage database at {storage_path} has no '{required_key}'.\nPlease sign in with the CardinalDL GUI, or run:\n./cardinaldl --login --username 'your_provided_CDL_username' --password 'your_provided_CDL_password' --configpath '/path/to/storage.db'")

    # the CLI stores every value as JSON so the device key should come back as an object
    try:
        device_key = json.loads(stored_values["accountDeviceProofKeyV2"])
    except ValueError as parse_error:
        return (False, f"Could not read the CardinalDL device key in {storage_path}: {parse_error}\nPlease sign in again so it gets rebuilt.")

    if not isinstance(device_key, dict):
        return (False, f"The CardinalDL device key in {storage_path} is not in the expected format.\nPlease sign in again so it gets rebuilt.")

    # linux builds have no secret protector so a key protected on windows can never be unlocked here
    key_provider = device_key.get("provider")
    if key_provider != "plain":
        return (False, f"The CardinalDL storage DB at {storage_path} has the device key provider '{key_provider}', but linux builds can only read 'plain'.\nIt seems like you copy-pasted your DB from windows to linux without running the login command as you have the wrong auth provider.\nPlease 'docker compose down' this container and run:\n./cardinaldl --login --username 'your_provided_CDL_username' --password 'your_provided_CDL_password' --configpath '/path/to/storage.db'")

    return (True, "")


def _log(message: str, level: str = "info") -> None:
    """Internal logging helper function. Needed to avoid circular imports."""

    try:
        from appdata.modules.Globals import log_manager
    except Exception:
        return

    try:
        match level:
            case "debug":
                log_manager.debug(message)
            case "warning":
                log_manager.warning(message)
            case "error":
                log_manager.error(message)
            case _:
                log_manager.info(message)
    except Exception:
        pass


def load_defaults(storage_path: str) -> tuple[list[str], list[str]]:
    """Read defaultDubs and defaultSubs from storage.db."""

    def _normalize_default_codes(raw_codes) -> list[str]:
        codes = []
        if not isinstance(raw_codes, list):
            return codes

        for raw_code in raw_codes:
            normalized = str(raw_code).strip().upper()
            if normalized == "":
                continue
            if normalized not in VALID_CDL_CODES:
                continue
            codes.append(normalized)

        return dedupe_casefold(codes)

    default_dubs = []
    default_subs = []

    if not os.path.isfile(storage_path):
        _CDL_DEFAULTS[storage_path] = ([], [])
        return [], []

    try:
        connection = sqlite3.connect(storage_path)
        try:
            rows = connection.execute("SELECT key, value FROM kv_store WHERE key IN ('defaultDubs', 'defaultSubs')").fetchall()
        finally:
            connection.close()
    except sqlite3.Error as db_error:
        _log(f"Could not read CardinalDL storage defaults from {storage_path}: {db_error}", level="warning")
        _CDL_DEFAULTS[storage_path] = ([], [])
        return [], []

    for stored_key, stored_value in rows:
        try:
            parsed_value = json.loads(stored_value)
        except (ValueError, TypeError):
            continue

        match stored_key:
            case "defaultDubs":
                default_dubs = _normalize_default_codes(parsed_value)
            case "defaultSubs":
                default_subs = _normalize_default_codes(parsed_value)

    _CDL_DEFAULTS[storage_path] = (default_dubs, default_subs)
    return default_dubs, default_subs


def normalize_video_qualities(raw_qualities) -> dict[str, list[str]]:
    normalized = {}
    if not isinstance(raw_qualities, dict):
        return normalized

    for raw_resolution, raw_suffixes in raw_qualities.items():
        resolution = str(raw_resolution).strip()
        if resolution == "":
            continue

        suffixes = []
        if isinstance(raw_suffixes, list):
            for raw_suffix in raw_suffixes:
                suffix = str(raw_suffix).strip()
                if suffix != "":
                    suffixes.append(suffix)

        normalized[resolution] = dedupe_casefold(suffixes)

    return normalized


def normalize_audio_qualities(raw_audios) -> dict[str, list[str]]:
    normalized = {}
    if not isinstance(raw_audios, dict):
        return normalized

    for raw_code, raw_suffixes in raw_audios.items():
        code = str(raw_code).strip()
        if code == "":
            continue

        if code not in VALID_CDL_CODES:
            _log(
                f"CardinalDL CLI output unknown dub code '{raw_code}'. Skipping it.\nIf you believe this is a mistake, please open an issue with details about the dub language and service it was found in so it can be added to the mapping.",
                level="warning"
            )
            continue

        suffixes = []
        if isinstance(raw_suffixes, list):
            for raw_suffix in raw_suffixes:
                suffix = str(raw_suffix).strip()
                if suffix != "":
                    suffixes.append(suffix)

        normalized[code] = dedupe_casefold(suffixes)

    return normalized


def normalize_subtitles(raw_subtitles: list) -> list[str]:
    cleaned = []
    for raw_subtitle in raw_subtitles:
        code = str(raw_subtitle).strip()
        if code == "":
            continue

        if code not in VALID_CDL_CODES:
            _log(
                f"CardinalDL CLI output unknown subtitle code '{raw_subtitle}'. Skipping it.\nIf you believe this is a mistake, please open an issue with details about the subtitle language and service it was found in so it can be added to the mapping.",
                level="warning"
            )
            continue

        cleaned.append(code)

    return dedupe_casefold(cleaned)


def select_video(service: Service, episode: Episode) -> str | None:
    cdl_service_config = service.config

    videoquality = cdl_service_config.videoquality.strip()
    if videoquality == "":
        return None

    if cdl_service_config.fallback:
        _log(f"Using CardinalDL videoquality as configured (fallback on): {videoquality}", level="debug")
        return videoquality

    quality_parts = videoquality.lower().split("@")
    resolution = quality_parts[0].strip() if len(quality_parts) > 0 else ""
    codec = quality_parts[1].strip() if len(quality_parts) > 1 else ""
    video_range = quality_parts[2].strip() if len(quality_parts) > 2 else ""

    available_video_qualities = episode.available_video_qualities
    if resolution == "" or resolution == "highest":
        suffix_lists = list(available_video_qualities.values())
    else:
        suffix_lists = []
        for stored_resolution, stored_suffixes in available_video_qualities.items():
            if stored_resolution.lower().rstrip("p") == resolution.rstrip("p"):
                suffix_lists.append(stored_suffixes)

    quality_available = False
    for suffixes in suffix_lists:
        for suffix in suffixes:
            suffix_parts = suffix.split("@")
            suffix_codec = suffix_parts[0].strip().lower() if len(suffix_parts) > 0 else ""
            suffix_range = suffix_parts[1].strip().lower() if len(suffix_parts) > 1 else ""

            codec_ok = codec == "" or codec == suffix_codec
            if video_range == "":
                range_ok = True
            elif video_range == "dv":
                range_ok = suffix_range in DV_VIDEO_RANGES
            else:
                range_ok = video_range == suffix_range

            if codec_ok and range_ok:
                quality_available = True
                break
        if quality_available:
            break

    if quality_available:
        _log(f"Requested CardinalDL videoquality is available: {videoquality}", level="debug")
        return videoquality

    _log(f"Requested CardinalDL videoquality '{videoquality}' is not available and fallback is off. Letting CardinalDL choose automatically.", level="debug")
    return None


def select_dubs(service: Service, episode: Episode, dub_overrides: list[str] | None = None):
    available_cdl_dubs = set()
    for dub_code in episode.available_dubs:
        normalized = dub_code.strip().upper()
        if normalized == "":
            continue
        available_cdl_dubs.add(normalized)

    _log(f"Available CardinalDL dubs: {available_cdl_dubs}", level="debug")

    if dub_overrides is not None:
        desired_override_dubs = []
        for language_code in dub_overrides:
            normalized = language_code.strip().upper()
            if normalized == "":
                continue
            desired_override_dubs.append(normalized)

        desired_override_dubs = dedupe_casefold(desired_override_dubs)

        _log(f"Season CardinalDL dub overrides: {desired_override_dubs}", level="debug")

        selected_override_dubs = []
        for language_code in desired_override_dubs:
            if language_code not in available_cdl_dubs:
                continue
            selected_override_dubs.append(language_code)

        selected_override_dubs = dedupe_casefold(selected_override_dubs)

        if selected_override_dubs:
            _log(f"Using season CardinalDL dub overrides: {selected_override_dubs}", level="debug")
            return selected_override_dubs

        _log("No season CardinalDL dub overrides are available for this episode. Skipping it.", level="debug")
        return False

    cdl_service_config = service.config

    desired_cdl_dubs = []
    for language_code in cdl_service_config.dublang:
        normalized = language_code.strip().upper()
        if normalized == "":
            continue
        desired_cdl_dubs.append(normalized)

    desired_cdl_dubs = dedupe_casefold(desired_cdl_dubs)

    if not desired_cdl_dubs:
        _log("No CardinalDL dubs configured for this service. Deferring to CardinalDL storage defaults.", level="debug")
        return None

    backup_cdl_dubs = []
    for language_code in cdl_service_config.backup_dubs:
        normalized = language_code.strip().upper()
        if normalized == "":
            continue
        backup_cdl_dubs.append(normalized)

    backup_cdl_dubs = dedupe_casefold(backup_cdl_dubs)

    _log(f"Desired CardinalDL dubs: {desired_cdl_dubs}", level="debug")
    _log(f"Backup CardinalDL dubs: {backup_cdl_dubs}", level="debug")

    selected_desired = []
    for language_code in desired_cdl_dubs:
        if language_code not in available_cdl_dubs:
            continue
        selected_desired.append(language_code)
    selected_desired = dedupe_casefold(selected_desired)

    if selected_desired:
        _log(f"Desired CardinalDL dubs available: {selected_desired}", level="debug")
        return selected_desired

    selected_backup = []
    for language_code in backup_cdl_dubs:
        if language_code not in available_cdl_dubs:
            continue
        selected_backup.append(language_code)
    selected_backup = dedupe_casefold(selected_backup)

    if selected_backup:
        _log(f"Desired CardinalDL dubs not available, but backup dubs are: {selected_backup}", level="debug")
        return selected_backup

    if available_cdl_dubs and config.app.fallback_to_any_dub:
        _log("Neither desired nor backup CardinalDL dubs are available. Falling back to first available dub.", level="debug")
        first_dub = next(iter(sorted(available_cdl_dubs)))
        return [first_dub]

    _log("No CardinalDL dubs available at all for this episode. Skipping it.", level="debug")
    return False


def select_subs(service: Service, episode: Episode, sub_overrides: list[str] | None = None):
    cdl_service_config = service.config

    available_cdl_subs = set()
    for locale_code in episode.available_subs:
        normalized = locale_code.strip().upper()
        if normalized == "":
            continue
        available_cdl_subs.add(normalized)

    _log(f"Available CardinalDL subs: {available_cdl_subs}", level="debug")

    if sub_overrides is None:
        desired_sub_source = []
        for locale_code in cdl_service_config.dlsubs:
            desired_sub_source.append(locale_code)
        _log(f"Using CardinalDL default subs from config: {desired_sub_source}", level="debug")
    else:
        desired_sub_source = []
        for locale_code in sub_overrides:
            desired_sub_source.append(locale_code)
        _log(f"Using CardinalDL season sub overrides: {desired_sub_source}", level="debug")

    requested_cli_subs = []
    matched_subs = []

    for locale_code in desired_sub_source:
        normalized = locale_code.strip().upper()
        if normalized == "":
            continue

        if normalized not in VALID_CDL_CODES:
            continue

        requested_cli_subs.append(normalized)

        if normalized in available_cdl_subs:
            matched_subs.append(normalized)

    matched_subs = dedupe_casefold(matched_subs)
    requested_cli_subs = dedupe_casefold(requested_cli_subs)

    if matched_subs:
        _log(f"Using CardinalDL subs matched from available metadata: {matched_subs}", level="debug")
        return matched_subs

    if requested_cli_subs:
        _log(
            f"Could not match requested CardinalDL subs against parsed subtitle metadata. Passing requested subs to CLI anyway: {requested_cli_subs}",
            level="debug"
        )
        return requested_cli_subs

    _log("No CardinalDL subs are available for this episode. Skipping subtitle override.", level="debug")
    return None


def _format_audio_entry(lang: str, audio_format: str, channels: str) -> str:
    spec = audio_format
    if channels != "":
        spec = f"{spec}@{channels}"
    if lang != "":
        return f"{lang}:{spec}"
    return spec


def _audio_quality_available(suffixes: list[str], audio_format: str, channels: str) -> bool:
    if not suffixes:
        return False

    for suffix in suffixes:
        suffix_parts = suffix.split("@")
        suffix_format = suffix_parts[0].strip().lower() if len(suffix_parts) > 0 else ""
        suffix_channels = suffix_parts[1].strip().lower() if len(suffix_parts) > 1 else ""

        format_ok = audio_format == "" or audio_format == suffix_format
        channels_ok = channels == "" or channels == suffix_channels
        if format_ok and channels_ok:
            return True

    return False


def select_audio(service: Service, episode: Episode, selected_dubs: list[str] | bool | None) -> str | None:
    cdl_service_config = service.config

    dubs = []
    if selected_dubs:
        for dub_code in selected_dubs:
            normalized = str(dub_code).strip().upper()
            if normalized != "":
                dubs.append(normalized)

    if dubs == []:
        return None

    audioquality = cdl_service_config.audioquality.strip()
    if audioquality == "":
        return None

    available = episode.available_audio_qualities

    kept = []
    for raw_entry in audioquality.split(","):
        entry = raw_entry.strip()
        if entry == "":
            continue

        if ":" in entry:
            lang_part, spec = entry.split(":", 1)
            lang = lang_part.strip().upper()
        else:
            lang = ""
            spec = entry

        spec_parts = spec.split("@")
        audio_format = spec_parts[0].strip().lower() if len(spec_parts) > 0 else ""
        channels = spec_parts[1].strip().lower() if len(spec_parts) > 1 else ""

        # audioquality never forces a dub select_dubs did not pick
        if lang != "" and lang not in dubs:
            continue

        if cdl_service_config.fallback:
            kept.append(_format_audio_entry(lang, audio_format, channels))
            continue

        if lang != "":
            if _audio_quality_available(available.get(lang, []), audio_format, channels):
                kept.append(_format_audio_entry(lang, audio_format, channels))
            continue

        # language-less entry, fallback off. expand per selected dub that has it
        for dub in dubs:
            if _audio_quality_available(available.get(dub, []), audio_format, channels):
                kept.append(_format_audio_entry(dub, audio_format, channels))

    if kept == []:
        return None

    joined = ",".join(kept)
    _log(f"Selected CardinalDL audioquality: {joined}", level="debug")
    return joined


def get_wanted_dubs_and_subs(service: Service, series_id: str, season_id: str | None) -> tuple[set, set]:
    season_monitor = None
    if season_id is not None:
        series_config = service.monitor_series_id.get(series_id)
        if series_config is not None:
            season_monitor = series_config.get(season_id)

    cdl_service_config = service.config

    default_dubs, default_subs = _CDL_DEFAULTS.get(cdl_service_config.configpath, ([], []))

    if season_monitor is not None and season_monitor.dub_overrides is not None:
        dub_source = season_monitor.dub_overrides
    elif cdl_service_config.dublang:
        dub_source = cdl_service_config.dublang
    else:
        dub_source = default_dubs

    if season_monitor is not None and season_monitor.sub_overrides is not None:
        sub_source = season_monitor.sub_overrides
    elif cdl_service_config.dlsubs:
        sub_source = cdl_service_config.dlsubs
    else:
        sub_source = default_subs

    wanted_dubs = set()
    for language_code in dub_source:
        normalized = language_code.strip().upper()
        if normalized:
            wanted_dubs.add(normalized)

    wanted_subs = set()
    for locale_code in sub_source:
        normalized = locale_code.strip().upper()
        if normalized:
            wanted_subs.add(normalized)

    _log(f"Effective wanted CardinalDL tracks for {service.service_name} {series_id}/{season_id}: dubs={wanted_dubs}, subs={wanted_subs}", level="debug")

    return wanted_dubs, wanted_subs


def probe_streams(file_path: str) -> tuple[set, set]:
    streams = ffprobe(file_path)
    if streams == []:
        return set(), set()

    audio_langs = set()
    sub_langs = set()

    for stream in streams:
        ffprobe_tags = stream.get("tags", {})
        ffprobe_lang = str(ffprobe_tags.get("language", "")).strip().lower()
        ffprobe_title = ffprobe_tags.get("title", "").strip()

        lang = ISO_B_TO_T.get(ffprobe_lang, ffprobe_lang)
        title = re.sub(r"\s*\[[^\]]*\]\s*", " ", ffprobe_title).strip()

        _log(f"Probing stream: codec_type={stream.get('codec_type')}, ffprobe_lang={ffprobe_lang}, ffprobe_title={ffprobe_title!r}, lang={lang}, title={title!r}", level="debug")

        mapped_code = None
        if title in LANG_MAP:
            mapped_code = LANG_MAP[title][0]
        elif lang:
            for _, (cdl_code, iso) in LANG_MAP.items():
                if iso == lang:
                    mapped_code = cdl_code
                    break

        codec_type = stream.get("codec_type")

        match codec_type:
            case "audio":
                if mapped_code is not None:
                    audio_langs.add(mapped_code)
            case "subtitle":
                if mapped_code is not None:
                    sub_langs.add(mapped_code)
            case _:
                continue

    _log(f"Probed {file_path}: CardinalDL audio langs={audio_langs}, sub langs={sub_langs}", level="debug")

    return audio_langs, sub_langs
