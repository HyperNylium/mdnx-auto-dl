import os

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
LANG_MAP: dict[str, str] = {
    "English": "EN",
    "English (India)": "EN",
    "English (UK)": "EN-GB",

    "Spanish": "LA-ES",
    "Spanish (Mexico)": "MX-ES",
    "Castilian": "ES",

    "Portuguese": "PT",
    "Portuguese (Portugal)": "PT-PT",

    "French": "FR",
    "French (Canada)": "FR-CA",

    "German": "DE",

    "Arabic": "AR",
    "Arabic (Saudi Arabia)": "AR",
    "Arabic (Modern Standard)": "AR-001",

    "Italian": "IT",
    "Russian": "RU",
    "Turkish": "TR",
    "Hindi": "HI",

    "Chinese (Mandarin, PRC)": "CN",
    "Chinese (Mainland China)": "CN",
    "Chinese (Taiwan)": "TW",
    "Chinese (Hong-Kong)": "HK",
    "Chinese (Simplified)": "CN",
    "Chinese (Traditional)": "TW",

    "Korean": "KO",
    "Catalan": "CA",
    "Polish": "PL",
    "Thai": "TH",
    "Tamil (India)": "TA",
    "Malay (Malaysia)": "MS",
    "Vietnamese": "VI",
    "Indonesian": "ID",
    "Telugu (India)": "TE",
    "Japanese": "JP",

    "Norwegian Bokmal": "NB",

    "Dutch": "NL",
    "Swedish": "SV",
    "Finnish": "FI",
    "Norwegian": "NO",
    "Greek": "EL",
    "Hebrew": "HE",
    "Ukrainian": "UK",
    "Persian": "FA",
    "Bengali": "BN",
    "Czech": "CS",
    "Romanian": "RO",
    "Hungarian": "HU",
    "Tagalog": "TL",
    "Khmer": "KM",
    "Burmese": "MY",
    "Mongolian": "MN",
    "Icelandic": "IS",
    "Slovak": "SK",
    "Kannada": "KN",
    "Malayalam": "ML",
    "Basque": "EU",
    "Galician": "GL",
    "Serbian": "SR",
    "Macedonian": "MK",
    "Croatian": "HR",
    "Slovenian": "SL",
    "Bulgarian": "BG",
}


VALID_ZLO_CODES: set[str] = set(LANG_MAP.values())


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

    _log(
        f"Effective wanted ZLO tracks for {service.service_name} {series_id}/{season_id}: dubs={wanted_dubs}, subs={wanted_subs}",
        level="debug"
    )

    return wanted_dubs, wanted_subs


def probe_streams(file_path: str) -> tuple[set, set]:
    streams = ffprobe(file_path)
    if streams == []:
        return set(), set()

    audio_langs = set()
    sub_langs = set()

    for stream in streams:
        tags = stream.get("tags", {})
        title = tags.get("title", "").strip()
        codec_type = stream.get("codec_type")

        match codec_type:
            case "audio":
                if title not in LANG_MAP:
                    continue
                audio_langs.add(LANG_MAP[title])
            case "subtitle":
                # ZLO tags subs as "<Language> [Full]".
                lookup_title = title.removesuffix(" [Full]").strip().lower()
                if not lookup_title:
                    continue
                matched_code = None
                for lang_name, lang_code in LANG_MAP.items():
                    if lang_name.lower() == lookup_title:
                        matched_code = lang_code
                        break
                if matched_code is None:
                    continue
                sub_langs.add(matched_code)
            case _:
                continue

    _log(
        f"Probed {file_path}: ZLO audio langs={audio_langs}, sub langs={sub_langs}",
        level="debug",
    )

    return audio_langs, sub_langs
