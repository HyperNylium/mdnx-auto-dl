import os
import re
import json
import subprocess

from appdata.modules.Vars import (
    config,
    BIN_DIR,
    dedupe_casefold, ffprobe
)
from appdata.modules.types.queue import Episode
from appdata.modules.types.service import Service


ZLO_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "zlo", "zlo7")
ZLO_SERVICE_CONFIG_PATH = os.path.join(os.path.expanduser("~"), "Documents", "zlo7")
ZLO_SERVICE_CONFIG_SETTINGS_PATH = os.path.join(ZLO_SERVICE_CONFIG_PATH, "settings")


# format is: "Language Name": "zlo_code"
LANG_MAP: dict[str, tuple[str, str | None]] = {
    "English": ("EN", "eng"),
    "English (India)": ("EN", None),
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
    "Chinese (Taiwan)": ("TW", None),
    "Chinese (Hong-Kong)": ("HK", None),
    "Chinese (Simplified)": ("CN", None),
    "Chinese (Traditional)": ("TW", None),

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
    "Bulgarian": ("BG", "bul")
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


VALID_ZLO_CODES: set[str] = {zlo_code for zlo_code, _ in LANG_MAP.values()}


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


def normalize_zlo_dubs(raw_dubs: list) -> list[str]:
    cleaned = []
    for raw_dub in raw_dubs:
        code = str(raw_dub).strip()
        if code == "":
            continue

        if code not in VALID_ZLO_CODES:
            _log(
                f"ZLO CLI output unknown dub code '{raw_dub}'. Skipping it.\nIf you believe this is a mistake, please open an issue with details about the dub language and service it was found in so it can be added to the mapping.",
                level="warning"
            )
            continue

        cleaned.append(code)

    return dedupe_casefold(cleaned)


def normalize_zlo_subtitles(raw_subtitles: list) -> list[str]:
    cleaned = []
    for raw_subtitle in raw_subtitles:
        code = str(raw_subtitle).strip()
        if code == "":
            continue

        if code not in VALID_ZLO_CODES:
            _log(
                f"ZLO CLI output unknown subtitle code '{raw_subtitle}'. Skipping it.\nIf you believe this is a mistake, please open an issue with details about the subtitle language and service it was found in so it can be added to the mapping.",
                level="warning"
            )
            continue

        cleaned.append(code)

    return dedupe_casefold(cleaned)


def normalize_zlo_qualities(raw_qualities: list) -> list[str]:
    normalized = []
    for raw_quality in raw_qualities:
        quality_name = str(raw_quality).strip()
        if quality_name == "":
            continue
        normalized.append(quality_name)

    return dedupe_casefold(normalized)


def select_dubs(service: Service, episode: Episode, dub_overrides: list[str] | None = None):
    available_zlo_dubs = set()
    for dub_code in episode.available_dubs:
        normalized = dub_code.strip().upper()
        if normalized == "":
            continue
        available_zlo_dubs.add(normalized)

    _log(f"Available ZLO dubs: {available_zlo_dubs}", level="debug")

    if dub_overrides is not None:
        desired_override_dubs = []
        for language_code in dub_overrides:
            normalized = language_code.strip().upper()
            if normalized == "":
                continue
            desired_override_dubs.append(normalized)

        desired_override_dubs = dedupe_casefold(desired_override_dubs)

        _log(f"Season ZLO dub overrides: {desired_override_dubs}", level="debug")

        selected_override_dubs = []
        for language_code in desired_override_dubs:
            if language_code not in available_zlo_dubs:
                continue
            selected_override_dubs.append(language_code)

        selected_override_dubs = dedupe_casefold(selected_override_dubs)

        if selected_override_dubs:
            _log(f"Using season ZLO dub overrides: {selected_override_dubs}", level="debug")
            return selected_override_dubs

        _log("No season ZLO dub overrides are available for this episode. Skipping it.", level="debug")
        return False

    zlo_service_config = service.config

    desired_zlo_dubs = []
    for language_code in zlo_service_config.dubLang:
        normalized = language_code.strip().upper()
        if normalized == "":
            continue
        desired_zlo_dubs.append(normalized)

    desired_zlo_dubs = dedupe_casefold(desired_zlo_dubs)

    backup_zlo_dubs = []
    for language_code in zlo_service_config.backup_dubs:
        normalized = language_code.strip().upper()
        if normalized == "":
            continue
        backup_zlo_dubs.append(normalized)

    backup_zlo_dubs = dedupe_casefold(backup_zlo_dubs)

    _log(f"Desired ZLO dubs: {desired_zlo_dubs}", level="debug")
    _log(f"Backup ZLO dubs: {backup_zlo_dubs}", level="debug")

    selected_desired = []
    for language_code in desired_zlo_dubs:
        if language_code not in available_zlo_dubs:
            continue
        selected_desired.append(language_code)
    selected_desired = dedupe_casefold(selected_desired)

    if selected_desired:
        _log(f"Desired ZLO dubs available: {selected_desired}", level="debug")
        return selected_desired

    selected_backup = []
    for language_code in backup_zlo_dubs:
        if language_code not in available_zlo_dubs:
            continue
        selected_backup.append(language_code)
    selected_backup = dedupe_casefold(selected_backup)

    if selected_backup:
        _log(f"Desired ZLO dubs not available, but backup dubs are: {selected_backup}", level="debug")
        return selected_backup

    if available_zlo_dubs and config.app.fallback_to_any_dub:
        _log("Neither desired nor backup ZLO dubs are available. Falling back to first available dub.", level="debug")
        first_dub = next(iter(sorted(available_zlo_dubs)))
        return [first_dub]

    _log("No ZLO dubs available at all for this episode. Skipping it.", level="debug")
    return False


def select_subs(service: Service, episode: Episode, sub_overrides: list[str] | None = None):
    zlo_service_config = service.config

    available_zlo_subs = set()
    for locale_code in episode.available_subs:
        normalized = locale_code.strip().upper()
        if normalized == "":
            continue
        available_zlo_subs.add(normalized)

    _log(f"Available ZLO subs: {available_zlo_subs}", level="debug")

    if sub_overrides is None:
        desired_sub_source = []
        for locale_code in zlo_service_config.dlsubs:
            desired_sub_source.append(locale_code)
        _log(f"Using ZLO default subs from config: {desired_sub_source}", level="debug")
    else:
        desired_sub_source = []
        for locale_code in sub_overrides:
            desired_sub_source.append(locale_code)
        _log(f"Using ZLO season sub overrides: {desired_sub_source}", level="debug")

    requested_cli_subs = []
    matched_subs = []

    for locale_code in desired_sub_source:
        normalized = locale_code.strip().upper()
        if normalized == "":
            continue

        if normalized not in VALID_ZLO_CODES:
            continue

        requested_cli_subs.append(normalized)

        if normalized in available_zlo_subs:
            matched_subs.append(normalized)

    matched_subs = dedupe_casefold(matched_subs)
    requested_cli_subs = dedupe_casefold(requested_cli_subs)

    if matched_subs:
        _log(f"Using ZLO subs matched from available metadata: {matched_subs}", level="debug")
        return matched_subs

    if requested_cli_subs:
        _log(
            f"Could not match requested ZLO subs against parsed subtitle metadata. Passing requested subs to CLI anyway: {requested_cli_subs}",
            level="debug"
        )
        return requested_cli_subs

    _log("No ZLO subs are available for this episode. Skipping subtitle override.", level="debug")
    return None


def get_wanted_dubs_and_subs(service: Service, series_id: str, season_id: str | None) -> tuple[set, set]:
    season_monitor = None
    if season_id is not None:
        series_config = service.monitor_series_id.get(series_id)
        if series_config is not None:
            season_monitor = series_config.get(season_id)

    zlo_service_config = service.config

    if season_monitor is not None and season_monitor.dub_overrides is not None:
        dub_source = season_monitor.dub_overrides
    else:
        dub_source = zlo_service_config.dubLang

    if season_monitor is not None and season_monitor.sub_overrides is not None:
        sub_source = season_monitor.sub_overrides
    else:
        sub_source = zlo_service_config.dlsubs

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

    _log(f"Effective wanted ZLO tracks for {service.service_name} {series_id}/{season_id}: dubs={wanted_dubs}, subs={wanted_subs}", level="debug")

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
            for _, (zlo_code, iso) in LANG_MAP.items():
                if iso == lang:
                    mapped_code = zlo_code
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

    _log(f"Probed {file_path}: ZLO audio langs={audio_langs}, sub langs={sub_langs}", level="debug")

    return audio_langs, sub_langs


def _get_last_packet_pts(file_path: str, stream_index: int) -> float | None:
    timeout = 180
    packet_cmd = ["ffprobe", "-v", "quiet", "-select_streams", str(stream_index), "-show_entries", "packet=pts_time", "-of", "csv=p=0", file_path]

    _log(f"Running ffprobe packet scan on stream {stream_index} of {file_path}", level="debug")

    try:
        packet_result = subprocess.run(packet_cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _log(f"ffprobe packet scan timed out on stream {stream_index} of {file_path}", level="error")
        return None

    # Iterate from the end so we stop as soon as we find a usable timestamp.
    # ffprobe can emit "N/A" or blank lines for packets that lack PTS info.
    last_pts = None
    for raw_line in reversed(packet_result.stdout.splitlines()):
        line = raw_line.strip()
        if line == "" or line == "N/A":
            continue
        try:
            last_pts = float(line)
            break
        except ValueError:
            continue

    return last_pts


def verify_download(file_path: str) -> bool:
    if not os.path.isfile(file_path):
        _log(f"Could not find file for integrity check: {file_path}", level="error")
        return False

    timeout = 60
    probe_cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", file_path]

    _log(f"Running ffprobe integrity probe on {file_path}", level="debug")

    try:
        probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        _log(f"verify_download: ffprobe show_format/show_streams timed out on {file_path}", level="error")
        return False

    try:
        probe_data = json.loads(probe_result.stdout)
    except json.JSONDecodeError as decode_error:
        _log(f"verify_download: ffprobe JSON decode error on {file_path}: {decode_error}", level="error")
        return False

    format_section = probe_data.get("format") or {}
    raw_duration = format_section.get("duration")

    if raw_duration is None:
        _log(f"verify_download: container duration is missing for {file_path}", level="error")
        return False

    try:
        container_duration = float(raw_duration)
    except (TypeError, ValueError):
        _log(f"verify_download: container duration is not a number for {file_path}: {raw_duration}", level="error")
        return False

    streams = probe_data.get("streams") or []
    if not isinstance(streams, list) or streams == []:
        _log(f"verify_download: no streams reported for {file_path}", level="error")
        return False

    # 2 second floor for normal encoder rounding and stream-end vs container-end mismatches.
    # Anything past that is treated as truncation.
    floor_seconds = 2.0

    for stream in streams:
        codec_type = stream.get("codec_type")
        if codec_type not in ("video", "audio"):
            continue

        stream_index = stream.get("index")
        if stream_index is None:
            continue

        last_pts = _get_last_packet_pts(file_path, stream_index)
        if last_pts is None:
            _log(f"Without packet PTS info, cannot verify integrity of stream {stream_index} ({codec_type}). Failing verification to be safe.", level="error")
            return False

        delta = container_duration - last_pts
        if delta > floor_seconds:
            _log(f"Stream {stream_index} ({codec_type}) ends at {last_pts:.2f}s but container claims {container_duration:.2f}s ({delta:.2f}s short). File is truncated.", level="error")
            return False

    _log(f"File {file_path} passed integrity check (container duration {container_duration:.2f}s, last packet PTS within {floor_seconds:.2f}s)", level="debug")
    return True
