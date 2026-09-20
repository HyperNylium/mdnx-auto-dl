from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# a subtitle token is a language code with an optional variant like EN or EN:cc
SubToken = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"(?i)^[A-Za-z][A-Za-z0-9-]*(:(full|cc|sdh|caption|both))?$")]

# a cardinaldl video quality string like 1080p@@sdr
VideoQuality = Annotated[str, StringConstraints(pattern=r"^(?:(?:\d{3,4}p?|highest)?(?:@(?:h264|hevc|vp8|vp9|av1)?(?:@(?:dv-hdr10\+?|hdr10\+?|hlg|sdr|dv)?)?)?)?$")]

# a cardinaldl audio quality string like aac@2.0
AudioQuality = Annotated[str, StringConstraints(pattern=r"^(?:(?:[A-Za-z][A-Za-z-]*:)?(?:(?:atmos|eac3|ac3|aac)(?:@(?:7\.1|5\.1|2\.0|1\.0))?|@(?:7\.1|5\.1|2\.0|1\.0))(?:,(?:[A-Za-z][A-Za-z-]*:)?(?:(?:atmos|eac3|ac3|aac)(?:@(?:7\.1|5\.1|2\.0|1\.0))?|@(?:7\.1|5\.1|2\.0|1\.0)))*)?$")]

# a trackforge profile is a comma list of items like AAC:2.0, EOS:2.0 or ORIG
TrackForgeProfile = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"(?i)^\s*(?:(?:AAC|AC3|EAC3|DTS|OPUS|FLAC|WAV|PCM|ORIG|EOS\+?(?:-(?:AAC|AC3|EAC3|DTS|OPUS|FLAC|WAV|PCM))?)(?::(?:1\.0|2\.0|5\.1|7\.1))?(?:\s*,\s*(?:AAC|AC3|EAC3|DTS|OPUS|FLAC|WAV|PCM|ORIG|EOS\+?(?:-(?:AAC|AC3|EAC3|DTS|OPUS|FLAC|WAV|PCM))?)(?::(?:1\.0|2\.0|5\.1|7\.1))?)*)?\s*$")]


class DestinationConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    dir: str = Field(min_length=1)
    folder_structure: str = Field(min_length=1)


class AppConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    temp_dir: str = Field("/app/appdata/temp", alias="TEMP_DIR")
    bin_dir: str = Field("/app/appdata/bin", alias="BIN_DIR")
    log_dir: str = Field("/app/appdata/logs", alias="LOG_DIR")

    mdnx_cr_enabled: bool = Field(False, alias="MDNX_CR_ENABLED")
    mdnx_cr_username: str = Field("", alias="MDNX_CR_USERNAME")
    mdnx_cr_password: str = Field("", alias="MDNX_CR_PASSWORD")

    mdnx_hidive_enabled: bool = Field(False, alias="MDNX_HIDIVE_ENABLED")
    mdnx_hidive_username: str = Field("", alias="MDNX_HIDIVE_USERNAME")
    mdnx_hidive_password: str = Field("", alias="MDNX_HIDIVE_PASSWORD")

    mdnx_adn_enabled: bool = Field(False, alias="MDNX_ADN_ENABLED")
    mdnx_adn_username: str = Field("", alias="MDNX_ADN_USERNAME")
    mdnx_adn_password: str = Field("", alias="MDNX_ADN_PASSWORD")

    cdl_cr_enabled: bool = Field(False, alias="CDL_CR_ENABLED")
    cdl_hidive_enabled: bool = Field(False, alias="CDL_HIDIVE_ENABLED")
    cdl_adn_enabled: bool = Field(False, alias="CDL_ADN_ENABLED")
    cdl_disney_enabled: bool = Field(False, alias="CDL_DISNEY_ENABLED")
    cdl_netflix_enabled: bool = Field(False, alias="CDL_NETFLIX_ENABLED")
    cdl_amazon_enabled: bool = Field(False, alias="CDL_AMAZON_ENABLED")

    backup_dubs: list[str] = Field(["zho"], alias="BACKUP_DUBS")

    check_missing_dub_sub: bool = Field(True, alias="CHECK_MISSING_DUB_SUB")
    cache_dubs_subs: bool = Field(True, alias="CACHE_DUBS_SUBS")
    check_for_updates_interval: int = Field(3600, alias="CHECK_FOR_UPDATES_INTERVAL")
    episode_dl_delay: int = Field(30, alias="EPISODE_DL_DELAY")

    mdnx_cr_force_reauth: bool = Field(False, alias="MDNX_CR_FORCE_REAUTH")
    mdnx_cr_skip_api_test: bool = Field(False, alias="MDNX_CR_SKIP_API_TEST")
    mdnx_hidive_force_reauth: bool = Field(False, alias="MDNX_HIDIVE_FORCE_REAUTH")
    mdnx_hidive_skip_api_test: bool = Field(False, alias="MDNX_HIDIVE_SKIP_API_TEST")
    mdnx_adn_force_reauth: bool = Field(False, alias="MDNX_ADN_FORCE_REAUTH")
    clear_queue: bool = Field(False, alias="CLEAR_QUEUE")

    only_create_queue: bool = Field(False, alias="ONLY_CREATE_QUEUE")
    skip_queue_refresh: bool = Field(False, alias="SKIP_QUEUE_REFRESH")
    fallback_to_any_dub: bool = Field(False, alias="FALLBACK_TO_ANY_DUB")
    skip_cdm_check: bool = Field(False, alias="SKIP_CDM_CHECK")
    dry_run: bool = Field(False, alias="DRY_RUN")

    log_level: str = Field("info", alias="LOG_LEVEL")
    max_log_archives: int = Field(5, alias="MAX_LOG_ARCHIVES")

    smtp_enabled: bool = Field(False, alias="SMTP_ENABLED")
    smtp_from: str = Field("", alias="SMTP_FROM")
    smtp_to: str = Field("", alias="SMTP_TO")
    smtp_host: str = Field("", alias="SMTP_HOST")
    smtp_username: str = Field("", alias="SMTP_USERNAME")
    smtp_password: str = Field("", alias="SMTP_PASSWORD")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_starttls: bool = Field(True, alias="SMTP_STARTTLS")

    ntfy_enabled: bool = Field(False, alias="NTFY_ENABLED")
    ntfy_url: str = Field("", alias="NTFY_URL")
    ntfy_token: str = Field("", alias="NTFY_TOKEN")
    ntfy_username: str = Field("", alias="NTFY_USERNAME")
    ntfy_password: str = Field("", alias="NTFY_PASSWORD")
    ntfy_priority: str = Field("", alias="NTFY_PRIORITY")
    ntfy_tags: list[str] = Field(default_factory=list, alias="NTFY_TAGS")

    gotify_enabled: bool = Field(False, alias="GOTIFY_ENABLED")
    gotify_url: str = Field("", alias="GOTIFY_URL")
    gotify_token: str = Field("", alias="GOTIFY_TOKEN")
    gotify_priority: int = Field(5, alias="GOTIFY_PRIORITY")

    discord_enabled: bool = Field(False, alias="DISCORD_ENABLED")
    discord_webhook_url: str = Field("", alias="DISCORD_WEBHOOK_URL")

    plex_url: str | None = Field(None, alias="PLEX_URL")
    plex_token: str | None = Field(None, alias="PLEX_TOKEN")
    plex_url_override: bool = Field(False, alias="PLEX_URL_OVERRIDE")

    jelly_url: str | None = Field(None, alias="JELLY_URL")
    jelly_api_key: str | None = Field(None, alias="JELLY_API_KEY")
    jelly_url_override: bool = Field(False, alias="JELLY_URL_OVERRIDE")


class SeasonMonitorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blacklists: list[str] | None = None
    season_override: str | None = None
    dub_overrides: list[str] | None = None
    sub_overrides: list[SubToken] | None = None
    dir_override: str | None = None
    folder_structure_override: str | None = None
    trackforge_profile: TrackForgeProfile | None = None


class MdnxBinPath(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    mkvmerge: str = "mkvmerge"
    mp4decrypt: str = "/app/appdata/bin/bento4/mp4decrypt"
    shaka: str = "/app/appdata/bin/shaka_packager/shaka"


class MdnxCliDefaults(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    q: int = 0
    partsize: int = 3
    dubLang: list[str] = ["jpn", "eng"]
    dlsubs: list[str] = ["en"]
    defaultAudio: str = "jpn"
    defaultSub: str = "eng"
    vstream: str = "androidtv"
    astream: str = "androidtv"
    tsd: bool = False


class MdnxDirPath(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    content: str = "/app/appdata/temp"
    fonts: str = "./fonts/"


class MdnxConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    bin_path: MdnxBinPath = Field(default_factory=MdnxBinPath, alias="bin-path")
    cli_defaults: MdnxCliDefaults = Field(default_factory=MdnxCliDefaults, alias="cli-defaults")
    dir_path: MdnxDirPath = Field(default_factory=MdnxDirPath, alias="dir-path")


class CdlServiceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")
    videoquality: VideoQuality = "1080p@@sdr"
    # for audioquality allow LANG:format@channels but dont allow @bitrate
    audioquality: AudioQuality = "aac@2.0"
    fallback: bool = True
    # keep hybrid as None so that if the user ticked the box to enable it in the GUI, it will be True, but if they didnt, it will be None and the default behavior will be used without us having to pass --hybrid to the CLI
    hybrid: bool | None = None
    outputformat: str = Field("mkv", pattern=r"^(?:mkv|mp4)?$")
    dublang: list[str] = ["JP", "EN"]
    dlsubs: list[SubToken] = ["EN"]
    forcesubformat: str = Field("", pattern="^(srt|ass|vtt|auto|raw|original)?$")
    backup_dubs: list[str] = Field(default_factory=list)
    full_listing: bool = True
    workers: int | None = Field(None, ge=1)
    dlpath: str = "/app/appdata/temp"
    temppath: str = "/tmp"
    configpath: str = "/app/appdata/bin/cardinaldl/config/storage/storage.db"


class CdlConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    crunchyroll: CdlServiceConfig = Field(default_factory=CdlServiceConfig)
    hidive: CdlServiceConfig = Field(default_factory=CdlServiceConfig)
    adn: CdlServiceConfig = Field(default_factory=CdlServiceConfig)
    disney: CdlServiceConfig = Field(default_factory=CdlServiceConfig)
    netflix: CdlServiceConfig = Field(default_factory=CdlServiceConfig)
    amazon: CdlServiceConfig = Field(default_factory=CdlServiceConfig)


class TrackForgeServiceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    enabled: bool = False
    workers: int = Field(1, ge=1)
    muxer: str = Field("auto", pattern=r"^(auto|ffmpeg|mkvmerge)$")
    profile: TrackForgeProfile = ""


class TrackForgeConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    services: dict[str, TrackForgeServiceConfig] = Field(default_factory=dict)


class ExtraFeaturesConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    trackforge: TrackForgeConfig = Field(default_factory=TrackForgeConfig)


class Config(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mdnx_cr_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    mdnx_hidive_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    mdnx_adn_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)

    cdl_cr_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    cdl_hidive_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    cdl_adn_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    cdl_disney_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    cdl_netflix_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    cdl_amazon_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)

    destinations: dict[str, DestinationConfig] = Field(default_factory=dict)

    app: AppConfig = Field(default_factory=AppConfig)
    mdnx: MdnxConfig = Field(default_factory=MdnxConfig)
    cardinaldl: CdlConfig = Field(default_factory=CdlConfig)
    extra_features: ExtraFeaturesConfig = Field(default_factory=ExtraFeaturesConfig)
