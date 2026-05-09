import os

from appdata.modules.Vars import (
    config,
    BIN_DIR,
    dedupe_casefold, _ffprobe
)
from appdata.modules.types.queue import Episode
from appdata.modules.types.service import Service


MDNX_SERVICE_BIN_PATH = os.path.join(BIN_DIR, "mdnx", "aniDL")
MDNX_SERVICE_CR_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "cr_token.yml")
MDNX_SERVICE_HIDIVE_TOKEN_PATH = os.path.join(BIN_DIR, "mdnx", "config", "hd_new_token.yml")
MDNX_SERVICE_WIDEVINE_PATH = os.path.join(BIN_DIR, "mdnx", "widevine")
MDNX_SERVICE_PLAYREADY_PATH = os.path.join(BIN_DIR, "mdnx", "playready")


MDNX_API_OK_LOGS = [
    "[mkvmerge Done]",
    "[mkvmerge] Mkvmerge finished",
]


# format is: "Language Name": ["mdnx_dub_code", "mdnx_sub_locale"]
LANG_MAP: dict[str, list[str | None]] = {
    "English": ["eng", "en"],
    "English (India)": ["eng", "en-IN"],
    "English (UK)": ["eng", "en"],

    "Spanish": ["spa-419", "es-419"],
    "Spanish (Mexico)": ["spa-419", "es-419"],
    "Spanish LatAm": ["spa", "es-419"],
    "Spanish Europe": ["spa-ES", "es-ES"],
    "Castilian": ["spa-ES", "es-ES"],

    "Portuguese": ["por", "pt-BR"],
    "Portuguese (Portugal)": ["por", "pt-PT"],

    "French": ["fra", "fr"],
    "French (Canada)": ["fra", "fr"],

    "German": ["deu", "de"],

    "Arabic": ["ara", "ar"],
    "Arabic (Saudi Arabia)": ["ara", "ar"],
    "Arabic (Modern Standard)": ["ara-ME", "ar"],

    "Italian": ["ita", "it"],
    "Russian": ["rus", "ru"],
    "Turkish": ["tur", "tr"],
    "Hindi": ["hin", "hi"],

    "Chinese (Mandarin, PRC)": ["cmn", "zh"],
    "Chinese (Mainland China)": ["zho", "zh-CN"],
    "Chinese (Taiwan)": ["chi", "zh-TW"],
    "Chinese (Hong-Kong)": ["zh-HK", "zh-HK"],
    "Chinese (Simplified)": ["zho", "zh-CN"],
    "Chinese (Traditional)": ["chi", "zh-TW"],

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


NAME_TO_CODE = {}
for language_name, language_values in LANG_MAP.items():
    dub_code = language_values[0]
    if dub_code is None:
        continue
    NAME_TO_CODE[language_name] = dub_code


VALID_LOCALES = set()
for language_values in LANG_MAP.values():
    subtitle_locale = language_values[1]
    if subtitle_locale is None:
        continue
    VALID_LOCALES.add(subtitle_locale)


CODE_TO_LOCALE = {}
for language_values in LANG_MAP.values():
    dub_code = language_values[0]
    subtitle_locale = language_values[1]

    if dub_code is None or subtitle_locale is None:
        continue

    lowered_dub_code = dub_code.lower()
    lowered_subtitle_locale = subtitle_locale.lower()

    if lowered_dub_code not in CODE_TO_LOCALE:
        CODE_TO_LOCALE[lowered_dub_code] = lowered_subtitle_locale


def _log(message: str, level: str = "info") -> None:
    """Internal log shim. Avoids circular imports at module-load time."""

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
            case "critical":
                log_manager.critical(message)
            case _:
                log_manager.info(message)
    except Exception:
        pass


def select_dubs(service: Service, episode: Episode, dub_overrides: list[str] | None = None):
    available_dubs = set()
    for dub_code in episode.available_dubs:
        available_dubs.add(dub_code.lower())

    _log(f"Available dubs: {available_dubs}", level="debug")

    if dub_overrides is not None:
        desired_override_dubs = []
        for language_code in dub_overrides:
            desired_override_dubs.append(language_code.lower())

        _log(f"Season dub overrides: {desired_override_dubs}", level="debug")

        selected_override_dubs = []
        for language_code in desired_override_dubs:
            if language_code not in available_dubs:
                continue
            selected_override_dubs.append(language_code)

        selected_override_dubs = dedupe_casefold(selected_override_dubs)

        if selected_override_dubs:
            _log(f"Using season dub overrides: {selected_override_dubs}", level="debug")
            return selected_override_dubs

        _log("No season dub overrides are available for this episode. Skipping it.", level="debug")
        return False

    desired_dubs = []
    for language_code in config.mdnx.cli_defaults.dubLang:
        normalized_dub_code = language_code.strip().lower()
        if normalized_dub_code == "":
            continue
        desired_dubs.append(normalized_dub_code)

    backup_dubs = []
    for language_code in config.app.backup_dubs:
        backup_dubs.append(language_code.lower())

    _log(f"Desired dubs: {desired_dubs}", level="debug")
    _log(f"Backup dubs: {backup_dubs}", level="debug")

    desired_dubs_available = False
    for language_code in desired_dubs:
        if language_code in available_dubs:
            desired_dubs_available = True
            break

    if desired_dubs_available:
        _log("Desired dubs are available. Using service defaults.", level="debug")
        return None

    selected_backup_dubs = []
    for language_code in backup_dubs:
        if language_code not in available_dubs:
            continue
        selected_backup_dubs.append(language_code)

    selected_backup_dubs = dedupe_casefold(selected_backup_dubs)

    if selected_backup_dubs:
        _log(f"Desired dubs not available, but backup dubs are: {selected_backup_dubs}", level="debug")
        return selected_backup_dubs

    if available_dubs and config.app.fallback_to_any_dub:
        _log("Neither desired nor backup dubs are available. Falling back to first available dub.", level="debug")
        first_dub = next(iter(sorted(available_dubs)))
        return [first_dub]

    _log("No dubs available at all for this episode. Skipping it.", level="debug")
    return False


def select_subs(service: Service, episode: Episode, sub_overrides: list[str] | None = None):
    available_subs = set()
    for locale_code in episode.available_subs:
        available_subs.add(locale_code.lower())

    _log(f"Available subs: {available_subs}", level="debug")

    if sub_overrides is None:
        _log("No season sub overrides set. Not passing subtitle CLI override.", level="debug")
        return None

    desired_override_subs = []
    for locale_code in sub_overrides:
        desired_override_subs.append(locale_code.lower())

    _log(f"Season sub overrides: {desired_override_subs}", level="debug")

    selected_override_subs = []
    for locale_code in desired_override_subs:
        if locale_code not in available_subs:
            continue
        selected_override_subs.append(locale_code)

    selected_override_subs = dedupe_casefold(selected_override_subs)

    if selected_override_subs:
        _log(f"Using season sub overrides: {selected_override_subs}", level="debug")
        return selected_override_subs

    _log("No season sub overrides are available for this episode. Skipping subtitle override.", level="debug")
    return None


def get_wanted_dubs_and_subs(service: Service, series_id: str, season_id: str | None) -> tuple[set, set]:
    season_monitor = None
    if season_id is not None:
        series_config = service.monitor_series_id.get(series_id)
        if series_config is not None:
            season_monitor = series_config.get(season_id)

    if season_monitor is not None and season_monitor.dub_overrides is not None:
        dub_source = season_monitor.dub_overrides
    else:
        dub_source = config.mdnx.cli_defaults.dubLang

    if season_monitor is not None and season_monitor.sub_overrides is not None:
        sub_source = season_monitor.sub_overrides
    else:
        sub_source = config.mdnx.cli_defaults.dlsubs

    wanted_dubs = set()
    for language_code in dub_source:
        normalized = language_code.strip().lower()
        if normalized:
            wanted_dubs.add(normalized)

    wanted_subs = set()
    for locale_code in sub_source:
        normalized = locale_code.strip().lower()
        if normalized:
            wanted_subs.add(normalized)

    _log(f"Effective wanted MDNX tracks for {service.service_name} {series_id}/{season_id}: dubs={wanted_dubs}, subs={wanted_subs}", level="debug")

    return wanted_dubs, wanted_subs


def probe_streams(file_path: str) -> tuple[set, set]:
    streams = _ffprobe(file_path)
    if streams == []:
        return set(), set()

    audio_langs = set()
    sub_langs = set()

    for stream in streams:
        tags = stream.get("tags", {})
        raw_lang = str(tags.get("language", "")).strip().lower()
        title = tags.get("title", "").strip()

        mapped_audio = None
        mapped_sub = None

        if title in LANG_MAP:
            language_values = LANG_MAP[title]
            if language_values[0] is not None:
                mapped_audio = language_values[0].lower()
            if language_values[1] is not None:
                mapped_sub = language_values[1].lower()

        codec_type = stream.get("codec_type")

        match codec_type:
            case "audio":
                if mapped_audio is not None:
                    audio_langs.add(mapped_audio)
                else:
                    audio_langs.add(raw_lang)
            case "subtitle":
                if mapped_sub is not None:
                    sub_langs.add(mapped_sub)
                elif raw_lang in CODE_TO_LOCALE:
                    sub_langs.add(CODE_TO_LOCALE[raw_lang])
                else:
                    sub_langs.add(raw_lang)
            case _:
                continue

    _log(f"Probed {file_path}: MDNX audio langs={audio_langs}, sub langs={sub_langs}", level="debug")

    return audio_langs, sub_langs


def format_value(val) -> str:
    """YAML-ish formatter for one MDNX config value."""

    if isinstance(val, bool):
        return "true" if val else "false"

    if isinstance(val, (int, float)):
        return str(val)

    if isinstance(val, list):
        formatted_elements = []
        for item in val:
            if isinstance(item, str):
                formatted_elements.append(f'"{item}"')
            else:
                formatted_elements.append(str(item))
        joined = ", ".join(formatted_elements)
        return f'[{joined}]'

    return f'"{val}"'


def update_mdnx_config() -> None:
    """Write bin-path.yml, cli-defaults.yml, and dir-path.yml from the current MdnxConfig."""

    _log("Updating MDNX config files with new settings from user config...")

    mdnx_config = config.mdnx.model_dump(by_alias=True)

    for mdnx_config_file, mdnx_config_settings in mdnx_config.items():
        file_path = os.path.join(BIN_DIR, "mdnx", "config", f"{mdnx_config_file}.yml")

        lines = []
        for setting_key, setting_value in mdnx_config_settings.items():
            formatted_value = format_value(setting_value)
            lines.append(f"{setting_key}: {formatted_value}\n")

        with open(file_path, "w", encoding="utf-8") as file_handle:
            file_handle.writelines(lines)

        _log(f"Updated {file_path} with new settings.", level="debug")

    _log("MDNX config updated.")
