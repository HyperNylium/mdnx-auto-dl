from pydantic import BaseModel, ConfigDict, Field


class AppConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    temp_dir: str = Field("/app/appdata/temp", alias="TEMP_DIR")
    bin_dir: str = Field("/app/appdata/bin", alias="BIN_DIR")
    log_dir: str = Field("/app/appdata/logs", alias="LOG_DIR")
    data_dir: str = Field("/data", alias="DATA_DIR")

    cr_enabled: bool = Field(False, alias="CR_ENABLED")
    cr_username: str = Field("", alias="CR_USERNAME")
    cr_password: str = Field("", alias="CR_PASSWORD")

    hidive_enabled: bool = Field(False, alias="HIDIVE_ENABLED")
    hidive_username: str = Field("", alias="HIDIVE_USERNAME")
    hidive_password: str = Field("", alias="HIDIVE_PASSWORD")

    backup_dubs: list[str] = Field(["zho"], alias="BACKUP_DUBS")
    folder_structure: str = Field(
        "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}",
        alias="FOLDER_STRUCTURE",
    )

    check_missing_dub_sub: bool = Field(True, alias="CHECK_MISSING_DUB_SUB")
    check_for_updates_interval: int = Field(3600, alias="CHECK_FOR_UPDATES_INTERVAL")
    episode_dl_delay: int = Field(30, alias="EPISODE_DL_DELAY")

    cr_force_reauth: bool = Field(False, alias="CR_FORCE_REAUTH")
    cr_skip_api_test: bool = Field(False, alias="CR_SKIP_API_TEST")
    hidive_force_reauth: bool = Field(False, alias="HIDIVE_FORCE_REAUTH")
    hidive_skip_api_test: bool = Field(False, alias="HIDIVE_SKIP_API_TEST")

    only_create_queue: bool = Field(False, alias="ONLY_CREATE_QUEUE")
    skip_queue_refresh: bool = Field(False, alias="SKIP_QUEUE_REFRESH")
    fallback_to_any_dub: bool = Field(False, alias="FALLBACK_TO_ANY_DUB")
    skip_cdm_check: bool = Field(False, alias="SKIP_CDM_CHECK")
    dry_run: bool = Field(False, alias="DRY_RUN")

    log_level: str = Field("info", alias="LOG_LEVEL")
    max_log_archives: int = Field(5, alias="MAX_LOG_ARCHIVES")

    notification_preference: str = Field("none", alias="NOTIFICATION_PREFERENCE")
    ntfy_script_path: str = Field("/app/appdata/config/ntfy.sh", alias="NTFY_SCRIPT_PATH")

    smtp_from: str = Field("", alias="SMTP_FROM")
    smtp_to: str = Field("", alias="SMTP_TO")
    smtp_host: str = Field("", alias="SMTP_HOST")
    smtp_username: str = Field("", alias="SMTP_USERNAME")
    smtp_password: str = Field("", alias="SMTP_PASSWORD")
    smtp_port: int = Field(587, alias="SMTP_PORT")
    smtp_starttls: bool = Field(True, alias="SMTP_STARTTLS")

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
    sub_overrides: list[str] | None = None


class MdnxBinPath(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    ffmpeg: str = "ffmpeg"
    ffprobe: str = "ffprobe"
    mkvmerge: str = "mkvmerge"
    mp4decrypt: str = "/app/appdata/bin/bento4/mp4decrypt"


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


class Config(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cr_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)
    hidive_monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]] = Field(default_factory=dict)

    app: AppConfig = Field(default_factory=AppConfig)
    mdnx: MdnxConfig = Field(default_factory=MdnxConfig)
