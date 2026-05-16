## Notes for config file usage

mdnx-auto-dl can read its config from either `appdata/config/config.json`, `appdata/config/config.yaml`, or `appdata/config/config.yml`.  
You only need one. The first one found (in that order) is the one used. You can also override the path with the `CONFIG_FILE` environment variable.

Both formats accept the exact same keys and values. Every option in this doc shows a JSON and a YAML example side by side.

### Where keys go
The config file has a few top-level sections:
- `app`: every UPPER_CASE option in this doc lives here.
- `destinations`: where each service saves its files. One entry per service. Each entry has a `dir` and a `folder_structure`.
- `cr_monitor_series_id`, `hidive_monitor_series_id`, `adn_monitor_series_id`, `zlo_cr_monitor_series_id`, `zlo_hidive_monitor_series_id`, `zlo_adn_monitor_series_id`, `zlo_disneyplus_monitor_series_id`, `zlo_amazon_monitor_series_id`: top-level (not under `app`). These hold the series IDs you want to watch per service.
- `mdnx`: passthrough config for [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx). Anything valid in `cli-defaults.yml` is valid here, as long as the option's `cli-default Entry` in [multi-downloader-nx's documentation](https://github.com/anidl/multi-downloader-nx/blob/master/docs/DOCUMENTATION.md) is not `NaN`.
- `zlo`: per-service config for the ZLO downloader. Has subsections `crunchyroll`, `hidive`, `adn`, `disneyplus`, and `amazon`.

If you leave an option out of your config file, the application will use the default value listed in this doc.  
The only config that doesnt have defaults is the `destinations` section. Every service you enable needs an entry in `destinations` or the app will exit with an error on startup. This is intentional to not make assumptions about where/how you want to save files.

### JSON formatting rules
Standard JSON formatting still applies:
- Separate list items with `,` (comma)
- Integers are plain numbers (not quoted)
- Anything in quotes is a string

### YAML formatting rules
Standard YAML formatting still applies:
- Indentation matters. The example file uses 4 spaces.
- Strings do not need quotes unless they contain special characters. Quoting them anyway is fine.
- Booleans are `true` or `false` (lowercase).
- Lists use `- ` per item or inline `[a, b, c]` syntax.

---

## Index

- [Paths](#paths)
    - [`TEMP_DIR`](#TEMP_DIR)
    - [`BIN_DIR`](#BIN_DIR)
    - [`LOG_DIR`](#LOG_DIR)
- [Destinations](#destinations)
- [AniDL services](#anidl-services)
    - [Crunchyroll](#crunchyroll)
        - [`CR_ENABLED`](#CR_ENABLED)
        - [`CR_USERNAME`](#CR_USERNAME)
        - [`CR_PASSWORD`](#CR_PASSWORD)
        - [`CR_FORCE_REAUTH`](#CR_FORCE_REAUTH)
        - [`CR_SKIP_API_TEST`](#CR_SKIP_API_TEST)
    - [HiDive](#hidive)
        - [`HIDIVE_ENABLED`](#HIDIVE_ENABLED)
        - [`HIDIVE_USERNAME`](#HIDIVE_USERNAME)
        - [`HIDIVE_PASSWORD`](#HIDIVE_PASSWORD)
        - [`HIDIVE_FORCE_REAUTH`](#HIDIVE_FORCE_REAUTH)
        - [`HIDIVE_SKIP_API_TEST`](#HIDIVE_SKIP_API_TEST)
    - [ADN](#adn)
        - [`ADN_ENABLED`](#ADN_ENABLED)
        - [`ADN_USERNAME`](#ADN_USERNAME)
        - [`ADN_PASSWORD`](#ADN_PASSWORD)
        - [`ADN_FORCE_REAUTH`](#ADN_FORCE_REAUTH)
- [ZLO services](#zlo-services)
    - [`ZLO_CR_ENABLED`](#ZLO_CR_ENABLED)
    - [`ZLO_HIDIVE_ENABLED`](#ZLO_HIDIVE_ENABLED)
    - [`ZLO_ADN_ENABLED`](#ZLO_ADN_ENABLED)
    - [`ZLO_DISNEYPLUS_ENABLED`](#ZLO_DISNEYPLUS_ENABLED)
    - [`ZLO_AMAZON_ENABLED`](#ZLO_AMAZON_ENABLED)
- [Library and downloads](#library-and-downloads)
    - [`BACKUP_DUBS`](#BACKUP_DUBS)
    - [`CHECK_MISSING_DUB_SUB`](#CHECK_MISSING_DUB_SUB)
    - [`CHECK_FOR_UPDATES_INTERVAL`](#CHECK_FOR_UPDATES_INTERVAL)
    - [`EPISODE_DL_DELAY`](#EPISODE_DL_DELAY)
    - [`FALLBACK_TO_ANY_DUB`](#FALLBACK_TO_ANY_DUB)
- [Queue and lifecycle](#queue-and-lifecycle)
    - [`ONLY_CREATE_QUEUE`](#ONLY_CREATE_QUEUE)
    - [`SKIP_QUEUE_REFRESH`](#SKIP_QUEUE_REFRESH)
    - [`CLEAR_QUEUE`](#CLEAR_QUEUE)
    - [`DRY_RUN`](#DRY_RUN)
    - [`SKIP_CDM_CHECK`](#SKIP_CDM_CHECK)
- [Logging](#logging)
    - [`LOG_LEVEL`](#LOG_LEVEL)
    - [`MAX_LOG_ARCHIVES`](#MAX_LOG_ARCHIVES)
- [Notifications](#notifications)
    - [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE)
    - [`NTFY_SCRIPT_PATH`](#NTFY_SCRIPT_PATH)
    - [`SMTP_FROM`](#SMTP_FROM)
    - [`SMTP_TO`](#SMTP_TO)
    - [`SMTP_HOST`](#SMTP_HOST)
    - [`SMTP_USERNAME`](#SMTP_USERNAME)
    - [`SMTP_PASSWORD`](#SMTP_PASSWORD)
    - [`SMTP_PORT`](#SMTP_PORT)
    - [`SMTP_STARTTLS`](#SMTP_STARTTLS)
- [Plex](#plex)
    - [`PLEX_URL`](#PLEX_URL)
    - [`PLEX_TOKEN`](#PLEX_TOKEN)
    - [`PLEX_URL_OVERRIDE`](#PLEX_URL_OVERRIDE)
- [Jellyfin](#jellyfin)
    - [`JELLY_URL`](#JELLY_URL)
    - [`JELLY_API_KEY`](#JELLY_API_KEY)
    - [`JELLY_URL_OVERRIDE`](#JELLY_URL_OVERRIDE)
- [Top-level monitor maps](#top-level-monitor-maps)
    - [`cr_monitor_series_id`](#cr_monitor_series_id)
    - [`hidive_monitor_series_id`](#hidive_monitor_series_id)
    - [`adn_monitor_series_id`](#adn_monitor_series_id)
    - [`zlo_cr_monitor_series_id`](#zlo_cr_monitor_series_id)
    - [`zlo_hidive_monitor_series_id`](#zlo_hidive_monitor_series_id)
    - [`zlo_adn_monitor_series_id`](#zlo_adn_monitor_series_id)
    - [`zlo_disneyplus_monitor_series_id`](#zlo_disneyplus_monitor_series_id)
    - [`zlo_amazon_monitor_series_id`](#zlo_amazon_monitor_series_id)
- [ZLO per-service options](#zlo-per-service-options)
    - [`q`](#zlo.q)
    - [`qf`](#zlo.qf)
    - [`dubLang`](#zlo.dubLang)
    - [`dlsubs`](#zlo.dlsubs)
    - [`backup_dubs`](#zlo.backup_dubs)
    - [`dlpath`](#zlo.dlpath)
    - [`tempPath`](#zlo.tempPath)
- [multi-downloader-nx options](#multi-downloader-nx-options)
    - [`bin-path`](#mdnx.bin-path)
    - [`dir-path`](#mdnx.dir-path)
    - [`cli-defaults`](#mdnx.cli-defaults)
- [Options for `folder_structure`](#options-for-folder_structure)
- [Options for `NOTIFICATION_PREFERENCE`](#options-for-notification_preference)
    - [SMTP setup](#smtp-notification_preference-smtp)
    - [ntfy setup](#ntfy-notification_preference-ntfy)
- [Media server options (Plex and Jellyfin)](#media-server-options-plex-and-jellyfin)
    - [Plex setup](#plex-plex_url)
    - [Jellyfin setup](#jellyfin-jelly_url--jelly_api_key)
- [Options for `PLEX_URL_OVERRIDE` and `JELLY_URL_OVERRIDE`](#options-for-plex_url_override-and-jelly_url_override)
    - [Plex override](#plex-override-plex_url_override)
    - [Jellyfin override](#jellyfin-override-jelly_url_override)
- [How to blacklist entire seasons or just specific episodes](#how-to-blacklist-entire-seasons-or-just-specific-episodes)
- [Environment variables](#environment-variables)
    - [`UID`](#UID)
    - [`GID`](#GID)
    - [`TZ`](#TZ)
    - [`CONFIG_FILE`](#CONFIG_FILE)
    - [`QUEUE_DB_FILE`](#QUEUE_DB_FILE)
    - [`BENTO4_URL`](#BENTO4_URL)
    - [`MDNX_URL`](#MDNX_URL)
    - [`SHAKA_URL`](#SHAKA_URL)
    - [`FREEZE`](#FREEZE)
    - [`REMOTE_SPECIALS_URL`](#REMOTE_SPECIALS_URL)

---

## Paths

### <a id="TEMP_DIR"></a>TEMP_DIR

| Default | Type | Description |
| :--- | :--- | :--- |
| `/app/appdata/temp` | string | Temporary staging directory. Raw downloads are written/muxed here before moving into your library. |

JSON:
```json
"app": {
    "TEMP_DIR": "/app/appdata/temp"
}
```
YAML:
```yaml
app:
    TEMP_DIR: "/app/appdata/temp"
```

### <a id="BIN_DIR"></a>BIN_DIR

| Default | Type | Description |
| :--- | :--- | :--- |
| `/app/appdata/bin` | string | Path containing bundled binaries inside the container. |

JSON:
```json
"app": {
    "BIN_DIR": "/app/appdata/bin"
}
```
YAML:
```yaml
app:
    BIN_DIR: "/app/appdata/bin"
```

### <a id="LOG_DIR"></a>LOG_DIR

| Default | Type | Description |
| :--- | :--- | :--- |
| `/app/appdata/logs` | string | Folder where active and archived logs are stored. |

JSON:
```json
"app": {
    "LOG_DIR": "/app/appdata/logs"
}
```
YAML:
```yaml
app:
    LOG_DIR: "/app/appdata/logs"
```

---

## Destinations

`destinations` is a **top-level** key (not under `app`). It tells the application where to put finished files for each service.  
Every service you enable needs its own entry. If a service is enabled and has no entry here, the app will exit with an error on startup.

Each entry has two keys:
- `dir`: the folder inside the container where files are saved. This must match the right side of one of your bind-mounts in `docker-compose.yaml` (for example, `/data/Anime`).
- `folder_structure`: the layout for series, seasons, and episodes under `dir`.  
 See [Options for `folder_structure`](#options-for-folder_structure) for the variables you can use.

Valid keys are: `crunchyroll`, `hidive`, `adn`, `zlo-crunchyroll`, `zlo-hidive`, `zlo-adn`, `zlo-disneyplus`, `zlo-amazon`.

JSON:
```json
"destinations": {
    "crunchyroll": {
        "dir": "/data/Anime",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "hidive": {
        "dir": "/data/Anime",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "adn": {
        "dir": "/data/Anime",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "zlo-crunchyroll": {
        "dir": "/data/Anime",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "zlo-hidive": {
        "dir": "/data/Anime",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "zlo-adn": {
        "dir": "/data/Anime",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "zlo-disneyplus": {
        "dir": "/data/TV Shows",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    },
    "zlo-amazon": {
        "dir": "/data/TV Shows",
        "folder_structure": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    }
}
```

YAML:
```yaml
destinations:
    crunchyroll:
        dir: "/data/Anime"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    hidive:
        dir: "/data/Anime"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    adn:
        dir: "/data/Anime"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    zlo-crunchyroll:
        dir: "/data/Anime"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    zlo-hidive:
        dir: "/data/Anime"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    zlo-adn:
        dir: "/data/Anime"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    zlo-disneyplus:
        dir: "/data/TV Shows"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
    zlo-amazon:
        dir: "/data/TV Shows"
        folder_structure: "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
```

You only need entries for services you enable. You can drop the rest.

---

## AniDL services

The three sections below cover the services that go through [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx) (anidl): Crunchyroll, HiDive, and ADN.

### Crunchyroll

#### <a id="CR_ENABLED"></a>CR_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable auth with the Crunchyroll multi-downloader-nx API and monitor any series IDs in `cr_monitor_series_id`. |

JSON:
```json
"app": {
    "CR_ENABLED": true
}
```
YAML:
```yaml
app:
    CR_ENABLED: true
```

#### <a id="CR_USERNAME"></a>CR_USERNAME

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | Crunchyroll username for authentication. |

JSON:
```json
"app": {
    "CR_USERNAME": "itsamemario@myemailprovider.com"
}
```
YAML:
```yaml
app:
    CR_USERNAME: "itsamemario@myemailprovider.com"
```

#### <a id="CR_PASSWORD"></a>CR_PASSWORD

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | Crunchyroll password for authentication. |

JSON:
```json
"app": {
    "CR_PASSWORD": "thisismypassword123"
}
```
YAML:
```yaml
app:
    CR_PASSWORD: "thisismypassword123"
```

#### <a id="CR_FORCE_REAUTH"></a>CR_FORCE_REAUTH

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, do a fresh Crunchyroll login and overwrite `cr_token.yml`. After it runs, the app flips this back to `false` on its own to not do a fresh login every time. |

JSON:
```json
"app": {
    "CR_FORCE_REAUTH": true
}
```
YAML:
```yaml
app:
    CR_FORCE_REAUTH: true
```

#### <a id="CR_SKIP_API_TEST"></a>CR_SKIP_API_TEST

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, skip the startup self-test that pokes the Crunchyroll API. |

JSON:
```json
"app": {
    "CR_SKIP_API_TEST": true
}
```
YAML:
```yaml
app:
    CR_SKIP_API_TEST: true
```

### HiDive

#### <a id="HIDIVE_ENABLED"></a>HIDIVE_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable auth with the HiDive multi-downloader-nx API and monitor any series IDs in `hidive_monitor_series_id`. |

JSON:
```json
"app": {
    "HIDIVE_ENABLED": true
}
```
YAML:
```yaml
app:
    HIDIVE_ENABLED: true
```

#### <a id="HIDIVE_USERNAME"></a>HIDIVE_USERNAME

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | HiDive username for authentication. |

JSON:
```json
"app": {
    "HIDIVE_USERNAME": "itsamemario@myemailprovider.com"
}
```
YAML:
```yaml
app:
    HIDIVE_USERNAME: "itsamemario@myemailprovider.com"
```

#### <a id="HIDIVE_PASSWORD"></a>HIDIVE_PASSWORD

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | HiDive password for authentication. |

JSON:
```json
"app": {
    "HIDIVE_PASSWORD": "thisismypassword123"
}
```
YAML:
```yaml
app:
    HIDIVE_PASSWORD: "thisismypassword123"
```

#### <a id="HIDIVE_FORCE_REAUTH"></a>HIDIVE_FORCE_REAUTH

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, do a fresh HiDive login and overwrite `hd_new_token.yml`. After it runs, the app flips this back to `false` on its own. |

JSON:
```json
"app": {
    "HIDIVE_FORCE_REAUTH": true
}
```
YAML:
```yaml
app:
    HIDIVE_FORCE_REAUTH: true
```

#### <a id="HIDIVE_SKIP_API_TEST"></a>HIDIVE_SKIP_API_TEST

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, skip the startup self-test that pokes the HiDive API. |

JSON:
```json
"app": {
    "HIDIVE_SKIP_API_TEST": true
}
```
YAML:
```yaml
app:
    HIDIVE_SKIP_API_TEST: true
```

### ADN

#### <a id="ADN_ENABLED"></a>ADN_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable auth with the ADN (Animation Digital Network) multi-downloader-nx API and monitor any series IDs in `adn_monitor_series_id`. |

JSON:
```json
"app": {
    "ADN_ENABLED": true
}
```
YAML:
```yaml
app:
    ADN_ENABLED: true
```

#### <a id="ADN_USERNAME"></a>ADN_USERNAME

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | ADN username for authentication. |

JSON:
```json
"app": {
    "ADN_USERNAME": "itsamemario@myemailprovider.com"
}
```
YAML:
```yaml
app:
    ADN_USERNAME: "itsamemario@myemailprovider.com"
```

#### <a id="ADN_PASSWORD"></a>ADN_PASSWORD

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | ADN password for authentication. |

JSON:
```json
"app": {
    "ADN_PASSWORD": "thisismypassword123"
}
```
YAML:
```yaml
app:
    ADN_PASSWORD: "thisismypassword123"
```

#### <a id="ADN_FORCE_REAUTH"></a>ADN_FORCE_REAUTH

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, do a fresh ADN login and overwrite the saved ADN token. After it runs, the app flips this back to `false` on its own. |

JSON:
```json
"app": {
    "ADN_FORCE_REAUTH": true
}
```
YAML:
```yaml
app:
    ADN_FORCE_REAUTH: true
```

---

## ZLO services

The five `ZLO_*_ENABLED` flags turn on the matching ZLO service. They all need a working `zlo7` linux CLI binary and an already-logged-in `settings` folder. See the ZLO sections in [get-started.md](get-started.md) for setup steps.

ZLO expects the user to handle auth from the GUI. So in order to use mdnx-auto-dl with ZLO, you need to do a manual login for each service you want to use, then copy your `settings` folder to whatever folder you mounted `/home/mdnx-auto-dl/Documents/zlo7` to.  
mdnx-auto-dl **does NOT** handle auth/auth checking for ZLO.

### <a id="ZLO_CR_ENABLED"></a>ZLO_CR_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable the ZLO Crunchyroll service and monitor any series IDs in `zlo_cr_monitor_series_id`. |

JSON:
```json
"app": {
    "ZLO_CR_ENABLED": true
}
```
YAML:
```yaml
app:
    ZLO_CR_ENABLED: true
```

### <a id="ZLO_HIDIVE_ENABLED"></a>ZLO_HIDIVE_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable the ZLO HiDive service and monitor any series IDs in `zlo_hidive_monitor_series_id`. |

JSON:
```json
"app": {
    "ZLO_HIDIVE_ENABLED": true
}
```
YAML:
```yaml
app:
    ZLO_HIDIVE_ENABLED: true
```

### <a id="ZLO_ADN_ENABLED"></a>ZLO_ADN_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable the ZLO Animation Digital Network service and monitor any series IDs in `zlo_adn_monitor_series_id`. |

JSON:
```json
"app": {
    "ZLO_ADN_ENABLED": true
}
```
YAML:
```yaml
app:
    ZLO_ADN_ENABLED: true
```

### <a id="ZLO_DISNEYPLUS_ENABLED"></a>ZLO_DISNEYPLUS_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable the ZLO Disney+ service and monitor any series IDs in `zlo_disneyplus_monitor_series_id`. |

JSON:
```json
"app": {
    "ZLO_DISNEYPLUS_ENABLED": true
}
```
YAML:
```yaml
app:
    ZLO_DISNEYPLUS_ENABLED: true
```

### <a id="ZLO_AMAZON_ENABLED"></a>ZLO_AMAZON_ENABLED

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, enable the ZLO Amazon Prime Video service and monitor any series IDs in `zlo_amazon_monitor_series_id`. |

JSON:
```json
"app": {
    "ZLO_AMAZON_ENABLED": true
}
```
YAML:
```yaml
app:
    ZLO_AMAZON_ENABLED: true
```

---

## Library and downloads

### <a id="BACKUP_DUBS"></a>BACKUP_DUBS

| Default | Type | Description |
| :--- | :--- | :--- |
| `["zho"]` | array of strings | List of dubs to download if the primary dubs (set in `mdnx.cli-defaults.dubLang`) are not available. |

JSON:
```json
"app": {
    "BACKUP_DUBS": ["zho"]
}
```
YAML:
```yaml
app:
    BACKUP_DUBS:
        - "zho"
```

### <a id="CHECK_MISSING_DUB_SUB"></a>CHECK_MISSING_DUB_SUB

| Default | Type | Description |
| :--- | :--- | :--- |
| `true` | boolean | When `true`, check episodes for missing dub or subtitle tracks. If an episode is missing a desired dub or subtitle, add it back to the queue for redownloading. |

JSON:
```json
"app": {
    "CHECK_MISSING_DUB_SUB": true
}
```
YAML:
```yaml
app:
    CHECK_MISSING_DUB_SUB: true
```

### <a id="CHECK_FOR_UPDATES_INTERVAL"></a>CHECK_FOR_UPDATES_INTERVAL

| Default | Type | Description |
| :--- | :--- | :--- |
| `3600` | number (seconds) | Seconds to wait between full library scans for new episodes or missing tracks. |

JSON:
```json
"app": {
    "CHECK_FOR_UPDATES_INTERVAL": 3600
}
```
YAML:
```yaml
app:
    CHECK_FOR_UPDATES_INTERVAL: 3600
```

### <a id="EPISODE_DL_DELAY"></a>EPISODE_DL_DELAY

| Default | Type | Description |
| :--- | :--- | :--- |
| `30` | number (seconds) | Wait time in seconds after each episode download. Helps with API rate limits. |

JSON:
```json
"app": {
    "EPISODE_DL_DELAY": 30
}
```
YAML:
```yaml
app:
    EPISODE_DL_DELAY: 30
```

### <a id="FALLBACK_TO_ANY_DUB"></a>FALLBACK_TO_ANY_DUB

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, if none of the desired or backup dubs are available for an episode, fall back to the first dub in alphabetical order instead of skipping the episode. |

JSON:
```json
"app": {
    "FALLBACK_TO_ANY_DUB": true
}
```
YAML:
```yaml
app:
    FALLBACK_TO_ANY_DUB: true
```

---

## Queue and lifecycle

### <a id="ONLY_CREATE_QUEUE"></a>ONLY_CREATE_QUEUE

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, only build/update the queue and download nothing. The app exits with code `0` after the queue is built. Make sure to set `restart: no` for the container in this mode or it'll get stuck in a restart loop. |

JSON:
```json
"app": {
    "ONLY_CREATE_QUEUE": true
}
```
YAML:
```yaml
app:
    ONLY_CREATE_QUEUE: true
```

### <a id="SKIP_QUEUE_REFRESH"></a>SKIP_QUEUE_REFRESH

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, skip refreshing the queue and go into the main loop using whatever data is already in the queue database. Only useful when testing other parts of the app and you don't want to wait for the queue to build. |

JSON:
```json
"app": {
    "SKIP_QUEUE_REFRESH": true
}
```
YAML:
```yaml
app:
    SKIP_QUEUE_REFRESH: true
```

### <a id="CLEAR_QUEUE"></a>CLEAR_QUEUE

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, drop every row from the queue database on startup, then flip itself back to `false` and exit so the container can restart with a clean slate. Useful if the queue gets into a bad state and you want a full rebuild on the next run. |

> [!NOTE]
> Note: The `queue.db` is simply the state. It mainly keeps track of what episodes you have already downloaded and what episodes have all desired dubs/subs so we can skip a `ffprobe` on the file.  
> Clearing the DB, or hell, deleting the `queue.db` file entirely, is not harmful.
> It will simply re-build and run a full check on your library to re-populate the DB.

JSON:
```json
"app": {
    "CLEAR_QUEUE": true
}
```
YAML:
```yaml
app:
    CLEAR_QUEUE: true
```

### <a id="DRY_RUN"></a>DRY_RUN

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, simulate downloads without actually downloading any files. Useful for testing your config. |

JSON:
```json
"app": {
    "DRY_RUN": true
}
```
YAML:
```yaml
app:
    DRY_RUN: true
```

### <a id="SKIP_CDM_CHECK"></a>SKIP_CDM_CHECK

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, skip the startup check for a working CDM. The CDM is required for downloading, so only set this to `true` if you have a working CDM and want to skip the check. |

JSON:
```json
"app": {
    "SKIP_CDM_CHECK": true
}
```
YAML:
```yaml
app:
    SKIP_CDM_CHECK: true
```

---

## Logging

### <a id="LOG_LEVEL"></a>LOG_LEVEL

| Default | Type | Description |
| :--- | :--- | :--- |
| `info` | string | Logging level. Options: `debug`, `info`, `warning`, `error`, `critical`. |

JSON:
```json
"app": {
    "LOG_LEVEL": "info"
}
```
YAML:
```yaml
app:
    LOG_LEVEL: "info"
```

### <a id="MAX_LOG_ARCHIVES"></a>MAX_LOG_ARCHIVES

| Default | Type | Description |
| :--- | :--- | :--- |
| `5` | number | Maximum number of archived log files to keep. Older logs beyond this number will be deleted. Old logs are archived into `.zip` files for compression. |

JSON:
```json
"app": {
    "MAX_LOG_ARCHIVES": 5
}
```
YAML:
```yaml
app:
    MAX_LOG_ARCHIVES: 5
```

---

## Notifications

### <a id="NOTIFICATION_PREFERENCE"></a>NOTIFICATION_PREFERENCE

| Default | Type | Description |
| :--- | :--- | :--- |
| `none` | string | Which notification service to use. Options: `none`, `smtp`, `ntfy`. See [Options for NOTIFICATION_PREFERENCE](#options-for-notification_preference) below for the per-option setup. |

JSON:
```json
"app": {
    "NOTIFICATION_PREFERENCE": "smtp"
}
```
YAML:
```yaml
app:
    NOTIFICATION_PREFERENCE: "smtp"
```

### <a id="NTFY_SCRIPT_PATH"></a>NTFY_SCRIPT_PATH

| Default | Type | Description |
| :--- | :--- | :--- |
| `/app/appdata/config/ntfy.sh` | string | Path to the ntfy.sh script inside the container. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `ntfy`. |

JSON:
```json
"app": {
    "NTFY_SCRIPT_PATH": "/app/appdata/config/ntfy.sh"
}
```
YAML:
```yaml
app:
    NTFY_SCRIPT_PATH: "/app/appdata/config/ntfy.sh"
```

### <a id="SMTP_FROM"></a>SMTP_FROM

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | Email address that notifications are sent from. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON:
```json
"app": {
    "SMTP_FROM": "notifications@example.com"
}
```
YAML:
```yaml
app:
    SMTP_FROM: "notifications@example.com"
```

### <a id="SMTP_TO"></a>SMTP_TO

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string or array of strings | Email address (or list of email addresses) to send notifications to. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON (single):
```json
"app": {
    "SMTP_TO": "you@example.com"
}
```
JSON (multiple):
```json
"app": {
    "SMTP_TO": ["you@example.com", "someone-else@example.com"]
}
```
YAML (single):
```yaml
app:
    SMTP_TO: "you@example.com"
```
YAML (multiple):
```yaml
app:
    SMTP_TO:
        - "you@example.com"
        - "someone-else@example.com"
```

### <a id="SMTP_HOST"></a>SMTP_HOST

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | SMTP server hostname. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON:
```json
"app": {
    "SMTP_HOST": "smtp.gmail.com"
}
```
YAML:
```yaml
app:
    SMTP_HOST: "smtp.gmail.com"
```

### <a id="SMTP_USERNAME"></a>SMTP_USERNAME

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | SMTP username. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON:
```json
"app": {
    "SMTP_USERNAME": "you@gmail.com"
}
```
YAML:
```yaml
app:
    SMTP_USERNAME: "you@gmail.com"
```

### <a id="SMTP_PASSWORD"></a>SMTP_PASSWORD

| Default | Type | Description |
| :--- | :--- | :--- |
| `""` | string | SMTP password. For Gmail, use an app password. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON:
```json
"app": {
    "SMTP_PASSWORD": "your-app-password"
}
```
YAML:
```yaml
app:
    SMTP_PASSWORD: "your-app-password"
```

### <a id="SMTP_PORT"></a>SMTP_PORT

| Default | Type | Description |
| :--- | :--- | :--- |
| `587` | number | SMTP server port. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON:
```json
"app": {
    "SMTP_PORT": 587
}
```
YAML:
```yaml
app:
    SMTP_PORT: 587
```

### <a id="SMTP_STARTTLS"></a>SMTP_STARTTLS

| Default | Type | Description |
| :--- | :--- | :--- |
| `true` | boolean | When `true`, use STARTTLS for SMTP connections. Only needed if [`NOTIFICATION_PREFERENCE`](#NOTIFICATION_PREFERENCE) is set to `smtp`. |

JSON:
```json
"app": {
    "SMTP_STARTTLS": true
}
```
YAML:
```yaml
app:
    SMTP_STARTTLS: true
```

---

## Plex

### <a id="PLEX_URL"></a>PLEX_URL

| Default | Type | Description |
| :--- | :--- | :--- |
| `null` | string or `null` | URL of the Plex server to notify. Must be the complete URL of your server. Example: `http://192.168.1.10:32400`. If `null`, Plex will not be notified. |

JSON:
```json
"app": {
    "PLEX_URL": "http://192.168.1.10:32400"
}
```
YAML:
```yaml
app:
    PLEX_URL: "http://192.168.1.10:32400"
```

### <a id="PLEX_TOKEN"></a>PLEX_TOKEN

| Default | Type | Description |
| :--- | :--- | :--- |
| `null` | string or `null` | Plex auth token. You **do not** need to set this manually. It is saved into this config option automatically after you authorize the app (check the logs on first boot!). |

JSON:
```json
"app": {
    "PLEX_TOKEN": "your-plex-token"
}
```
YAML:
```yaml
app:
    PLEX_TOKEN: "your-plex-token"
```

### <a id="PLEX_URL_OVERRIDE"></a>PLEX_URL_OVERRIDE

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, use the Plex library refresh URL exactly as provided in [`PLEX_URL`](#PLEX_URL) (for example, a single library refresh endpoint). See [Plex override](#plex-override-plex_url_override) below for examples. |

JSON:
```json
"app": {
    "PLEX_URL_OVERRIDE": true
}
```
YAML:
```yaml
app:
    PLEX_URL_OVERRIDE: true
```

---

## Jellyfin

### <a id="JELLY_URL"></a>JELLY_URL

| Default | Type | Description |
| :--- | :--- | :--- |
| `null` | string or `null` | URL of the Jellyfin server to notify. Must be the complete URL of your server. Example: `http://192.168.1.10:8096`. If `null`, Jellyfin will not be notified. |

JSON:
```json
"app": {
    "JELLY_URL": "http://192.168.1.10:8096"
}
```
YAML:
```yaml
app:
    JELLY_URL: "http://192.168.1.10:8096"
```

### <a id="JELLY_API_KEY"></a>JELLY_API_KEY

| Default | Type | Description |
| :--- | :--- | :--- |
| `null` | string or `null` | Jellyfin API key. |

JSON:
```json
"app": {
    "JELLY_API_KEY": "your-jellyfin-api-key"
}
```
YAML:
```yaml
app:
    JELLY_API_KEY: "your-jellyfin-api-key"
```

### <a id="JELLY_URL_OVERRIDE"></a>JELLY_URL_OVERRIDE

| Default | Type | Description |
| :--- | :--- | :--- |
| `false` | boolean | When `true`, use the Jellyfin library refresh URL exactly as provided in [`JELLY_URL`](#JELLY_URL) (for example, a single library refresh endpoint). See [Jellyfin override](#jellyfin-override-jelly_url_override) below for examples. |

JSON:
```json
"app": {
    "JELLY_URL_OVERRIDE": true
}
```
YAML:
```yaml
app:
    JELLY_URL_OVERRIDE: true
```

---

## Top-level monitor maps

These keys live at the **top level** of the config file, not inside `app`. They map series IDs to per-season blacklist and override settings. See [How to blacklist entire seasons or just specific episodes](#how-to-blacklist-entire-seasons-or-just-specific-episodes) for the full format.

### <a id="cr_monitor_series_id"></a>cr_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | Crunchyroll (AniDL) series IDs to monitor. Used when [`CR_ENABLED`](#CR_ENABLED) is `true`. |

JSON:
```json
{
    "cr_monitor_series_id": {
        "GG5H5XQ7D": {}
    }
}
```
YAML:
```yaml
cr_monitor_series_id:
    GG5H5XQ7D: {}
```

### <a id="hidive_monitor_series_id"></a>hidive_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | HiDive (AniDL) series IDs to monitor. Used when [`HIDIVE_ENABLED`](#HIDIVE_ENABLED) is `true`. |

JSON:
```json
{
    "hidive_monitor_series_id": {
        "1050": {}
    }
}
```
YAML:
```yaml
hidive_monitor_series_id:
    "1050": {}
```

### <a id="adn_monitor_series_id"></a>adn_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | ADN (AniDL) series IDs to monitor. Used when [`ADN_ENABLED`](#ADN_ENABLED) is `true`. |

JSON:
```json
{
    "adn_monitor_series_id": {
        "442": {}
    }
}
```
YAML:
```yaml
adn_monitor_series_id:
    "442": {}
```

### <a id="zlo_cr_monitor_series_id"></a>zlo_cr_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | Crunchyroll (ZLO) series IDs to monitor. Used when [`ZLO_CR_ENABLED`](#ZLO_CR_ENABLED) is `true`. |

JSON:
```json
{
    "zlo_cr_monitor_series_id": {
        "GG5H5XQ7D": {}
    }
}
```
YAML:
```yaml
zlo_cr_monitor_series_id:
    GG5H5XQ7D: {}
```

### <a id="zlo_hidive_monitor_series_id"></a>zlo_hidive_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | HiDive (ZLO) series IDs to monitor. Used when [`ZLO_HIDIVE_ENABLED`](#ZLO_HIDIVE_ENABLED) is `true`. |

JSON:
```json
{
    "zlo_hidive_monitor_series_id": {
        "1050": {}
    }
}
```
YAML:
```yaml
zlo_hidive_monitor_series_id:
    "1050": {}
```

### <a id="zlo_adn_monitor_series_id"></a>zlo_adn_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | ADN (ZLO) series IDs to monitor. Used when [`ZLO_ADN_ENABLED`](#ZLO_ADN_ENABLED) is `true`. |

JSON:
```json
{
    "zlo_adn_monitor_series_id": {
        "your-adn-series-id": {}
    }
}
```
YAML:
```yaml
zlo_adn_monitor_series_id:
    your-adn-series-id: {}
```

### <a id="zlo_disneyplus_monitor_series_id"></a>zlo_disneyplus_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | Disney+ (ZLO) series IDs to monitor. Used when [`ZLO_DISNEYPLUS_ENABLED`](#ZLO_DISNEYPLUS_ENABLED) is `true`. |

JSON:
```json
{
    "zlo_disneyplus_monitor_series_id": {
        "your-disney-series-id": {}
    }
}
```
YAML:
```yaml
zlo_disneyplus_monitor_series_id:
    your-disney-series-id: {}
```

### <a id="zlo_amazon_monitor_series_id"></a>zlo_amazon_monitor_series_id

| Default | Type | Description |
| :--- | :--- | :--- |
| `{}` | object | Amazon (ZLO) series IDs to monitor. Used when [`ZLO_AMAZON_ENABLED`](#ZLO_AMAZON_ENABLED) is `true`. |

JSON:
```json
{
    "zlo_amazon_monitor_series_id": {
        "your-amazon-series-id": {}
    }
}
```
YAML:
```yaml
zlo_amazon_monitor_series_id:
    your-amazon-series-id: {}
```

---

## ZLO per-service options

The `zlo` section in the config file has one subsection per ZLO service: `crunchyroll`, `hidive`, `adn`, `disneyplus`, and `amazon`. Each subsection takes the same keys, listed below.

### <a id="zlo.q"></a>q

| Default | Type | Description |
| :--- | :--- | :--- |
| `1080p@avc` | string | Quality string passed to the `zlo7` binary. The format is `"{resolution}@{codec}"`. Examples: `1080p@avc`, `720p@avc`, `1080p@hvc`, `720p@hvc`, `1080p@dvh`, `720p@dvh`. The available qualities depend on the service. |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "q": "1080p@avc"
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        q: "1080p@avc"
```

### <a id="zlo.qf"></a>qf

| Default | Type | Description |
| :--- | :--- | :--- |
| `true` | boolean | Quality fallback. When `true`, `zlo7` falls back to the next-best available quality if the requested one is missing. The fallback order is `1080p@avc -> 1080p@hvc -> 1080p@dvh -> 720p@avc -> 720p@hvc -> 720p@dvh -> ...` |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "qf": true
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        qf: true
```

### <a id="zlo.dubLang"></a>dubLang

| Default | Type | Description |
| :--- | :--- | :--- |
| `["JP", "EN"]` | array of strings | Dub language codes you want for ZLO downloads. ZLO uses its own two-letter codes (for example, `JP`, `EN`, `DE`, `FR`, `ES`) as shown in the GUI. |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "dubLang": ["JP", "EN"]
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        dubLang:
            - "JP"
            - "EN"
```

### <a id="zlo.dlsubs"></a>dlsubs

| Default | Type | Description |
| :--- | :--- | :--- |
| `["EN"]` | array of strings | Subtitle language codes you want. Same code format as `dubLang`. |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "dlsubs": ["EN"]
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        dlsubs:
            - "EN"
```

### <a id="zlo.backup_dubs"></a>backup_dubs

| Default | Type | Description |
| :--- | :--- | :--- |
| `[]` | array of strings | Backup dubs to fall back to per ZLO service if none of the desired `dubLang` are available. |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "backup_dubs": ["CN"]
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        backup_dubs:
            - "CN"
```

### <a id="zlo.dlpath"></a>dlpath

| Default | Type | Description |
| :--- | :--- | :--- |
| `/app/appdata/temp` | string | Where `zlo7` writes the downloaded MKV before mdnx-auto-dl picks it up. |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "dlpath": "/app/appdata/temp"
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        dlpath: "/app/appdata/temp"
```

### <a id="zlo.tempPath"></a>tempPath

| Default | Type | Description |
| :--- | :--- | :--- |
| `/tmp` | string | Scratch directory the `zlo7` binary uses for in-progress download segments. |

JSON:
```json
"zlo": {
    "crunchyroll": {
        "tempPath": "/tmp"
    }
}
```
YAML:
```yaml
zlo:
    crunchyroll:
        tempPath: "/tmp"
```

---

## multi-downloader-nx options

The `mdnx` section in the config file is a passthrough for [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx). It has three subsections: `bin-path`, `dir-path`, and `cli-defaults`. Any setting from [multi-downloader-nx's documentation](https://github.com/anidl/multi-downloader-nx/blob/master/docs/DOCUMENTATION.md) is valid here, as long as the option's `cli-default Entry` is not `NaN`.

You only need to set the keys you want to override. Anything you leave out keeps the default below.

### <a id="mdnx.bin-path"></a>bin-path

Paths to the helper binaries that multi-downloader-nx calls. The defaults below match what the container ships with, so you do not need to touch these unless you mount your own binaries.

| Key | Default | Type | Description |
| :--- | :--- | :--- | :--- |
| `ffmpeg` | `ffmpeg` | string | Path to the `ffmpeg` binary. |
| `ffprobe` | `ffprobe` | string | Path to the `ffprobe` binary. |
| `mkvmerge` | `mkvmerge` | string | Path to the `mkvmerge` binary. |
| `mp4decrypt` | `/app/appdata/bin/bento4/mp4decrypt` | string | Path to the `mp4decrypt` binary (from Bento4). |

JSON:
```json
"mdnx": {
    "bin-path": {
        "ffmpeg": "ffmpeg",
        "ffprobe": "ffprobe",
        "mkvmerge": "mkvmerge",
        "mp4decrypt": "/app/appdata/bin/bento4/mp4decrypt"
    }
}
```
YAML:
```yaml
mdnx:
    bin-path:
        ffmpeg: "ffmpeg"
        ffprobe: "ffprobe"
        mkvmerge: "mkvmerge"
        mp4decrypt: "/app/appdata/bin/bento4/mp4decrypt"
```

### <a id="mdnx.dir-path"></a>dir-path

Working directories that multi-downloader-nx uses.

| Key | Default | Type | Description |
| :--- | :--- | :--- | :--- |
| `content` | `/app/appdata/temp` | string | Where multi-downloader-nx writes finished episode files before mdnx-auto-dl moves them. |
| `fonts` | `./fonts/` | string | Folder used for embedded fonts during subtitle muxing. |

JSON:
```json
"mdnx": {
    "dir-path": {
        "content": "/app/appdata/temp",
        "fonts": "./fonts/"
    }
}
```
YAML:
```yaml
mdnx:
    dir-path:
        content: "/app/appdata/temp"
        fonts: "./fonts/"
```

### <a id="mdnx.cli-defaults"></a>cli-defaults

These are the default download settings for multi-downloader-nx. Only the keys below ship as defaults, but you can add any other valid `cli-defaults.yml` key here too.

| Key | Default | Type | Description |
| :--- | :--- | :--- | :--- |
| `q` | `0` | number | Quality. `0` means best available. |
| `partsize` | `3` | number | How many parts to download in parallel. |
| `dubLang` | `["jpn", "eng"]` | array of strings | Dub languages you want, in order. Uses ISO 639-3 codes. |
| `dlsubs` | `["en"]` | array of strings | Subtitle languages you want. |
| `defaultAudio` | `"jpn"` | string | Audio track to mark as default in the output file. |
| `defaultSub` | `"eng"` | string | Subtitle track to mark as default in the output file. |
| `vstream` | `"androidtv"` | string | Video stream profile. |
| `astream` | `"androidtv"` | string | Audio stream profile. |
| `tsd` | `false` | boolean | Kills all active Crunchyroll Streaming Sessions to prevent getting the `TOO_MANY_ACTIVE_STREAMS` error. Only applies to Crunchyroll. Use with caution, as it will kick anyone currently watching Crunchyroll on your account. |

JSON:
```json
"mdnx": {
    "cli-defaults": {
        "q": 0,
        "partsize": 3,
        "dubLang": ["jpn", "eng"],
        "dlsubs": ["en"],
        "defaultAudio": "jpn",
        "defaultSub": "eng",
        "vstream": "androidtv",
        "astream": "androidtv",
        "tsd": false
    }
}
```
YAML:
```yaml
mdnx:
    cli-defaults:
        q: 0
        partsize: 3
        dubLang:
            - "jpn"
            - "eng"
        dlsubs:
            - "en"
        defaultAudio: "jpn"
        defaultSub: "eng"
        vstream: "androidtv"
        astream: "androidtv"
        tsd: false
```

---

## Options for `folder_structure`

| Variable           | Example value                | Explanation |
| :----------------- | :--------------------------: | :---------- |
| `${seriesTitle}`   | `Kaiju No. 8`                | Sanitized series title (filesystem-unsafe characters replaced). |
| `${season}`        | `1`                          | Season number, no leading zeros. |
| `${seasonPadded}`  | `01`                         | Season number padded to two digits. |
| `${episode}`       | `1`                          | Episode number, no leading zeros. |
| `${episodePadded}` | `01`                         | Episode number padded to two digits. |
| `${episodeName}`   | `The Man Who Became a Kaiju` | Sanitized episode title. |

Example of `folder_structure` using the variables above:
```txt
${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}
```

This would result in the following folder structure:
```txt
Kaiju No. 8/S1/Kaiju No. 8 - S01E01
```

---

## Options for `NOTIFICATION_PREFERENCE`

| Option | Explanation |
| :----- | :---------- |
| `none` | No notifications will be sent. |
| `smtp` | Send notifications via SMTP email. Requires the `SMTP_*` keys to be filled in. |
| `ntfy` | Send notifications via ntfy.sh. Requires `NTFY_SCRIPT_PATH` and your own `ntfy.sh` script. |

### SMTP (`NOTIFICATION_PREFERENCE: "smtp"`)
Add the SMTP keys to your config file.

JSON example:
```json
"app": {
    "NOTIFICATION_PREFERENCE": "smtp",
    "SMTP_FROM": "who we sending as?",
    "SMTP_TO": "who we sending to?",
    "SMTP_HOST": "smtp.gmail.com, or whatever your email provider is",
    "SMTP_USERNAME": "your username. For gmail, this is your email address",
    "SMTP_PASSWORD": "your password. For gmail, this is your app password",
    "SMTP_PORT": 587,
    "SMTP_STARTTLS": true
}
```

YAML example:
```yaml
app:
    NOTIFICATION_PREFERENCE: "smtp"
    SMTP_FROM: "who we sending as?"
    SMTP_TO: "who we sending to?"
    SMTP_HOST: "smtp.gmail.com, or whatever your email provider is"
    SMTP_USERNAME: "your username. For gmail, this is your email address"
    SMTP_PASSWORD: "your password. For gmail, this is your app password"
    SMTP_PORT: 587
    SMTP_STARTTLS: true
```

`SMTP_TO` can also be a list of email addresses. See the [`SMTP_TO`](#SMTP_TO) section for both formats.

### ntfy (`NOTIFICATION_PREFERENCE: "ntfy"`)
JSON example:
```json
"app": {
    "NOTIFICATION_PREFERENCE": "ntfy",
    "NTFY_SCRIPT_PATH": "/app/appdata/config/ntfy.sh"
}
```

YAML example:
```yaml
app:
    NOTIFICATION_PREFERENCE: "ntfy"
    NTFY_SCRIPT_PATH: "/app/appdata/config/ntfy.sh"
```

Set `NTFY_URL` inside `appdata/config/ntfy.sh` to the URL of your ntfy server. To modify things like tags, edit the `ntfy.sh` script. You also need a bind-mount: `./appdata/config/ntfy.sh:/app/appdata/config/ntfy.sh`.

---

## Media server options (Plex and Jellyfin)

You can set up **Plex**, **Jellyfin**, or **both** at the same time.

- If [`PLEX_URL`](#PLEX_URL) is `null` (default), Plex will not be notified.
- If [`JELLY_URL`](#JELLY_URL) is `null` (default), Jellyfin will not be notified.

### Plex (`PLEX_URL`)
Set [`PLEX_URL`](#PLEX_URL) in your config file (see that section for JSON and YAML examples).

After running `docker compose up -d && docker compose logs -f`, you will see a log line like this:
```txt
Open this URL in a browser to authorize the app:
https://app.plex.tv/auth#?blablablablablablablabla
```

Open that URL in a browser, log in to your Plex account, and authorize the app. The application then saves the Plex token to [`PLEX_TOKEN`](#PLEX_TOKEN) automatically and continues startup. There is no need to set `PLEX_TOKEN` by hand. The auth window is 10 minutes. If you do not authorize within that time, the application will exit.

After you authorize the app, you should see this in the logs:
```txt
Authorization completed. Token stored.
User is authenticated. Testing library scan...
Scan triggered successfully.
Library scan successful.
...
```

You will not have to do the authorization step again unless you delete `PLEX_TOKEN` or remove the session from Authenticated Devices in your Plex account settings.

### Jellyfin (`JELLY_URL` + `JELLY_API_KEY`)
Set [`JELLY_URL`](#JELLY_URL) and [`JELLY_API_KEY`](#JELLY_API_KEY) in your config file (see those sections for JSON and YAML examples).

There is no manual authorization step like Plex. Make sure your API key is correct and you should be good to go.

---

## Options for `PLEX_URL_OVERRIDE` and `JELLY_URL_OVERRIDE`

By default, if you only set:
- [`PLEX_URL`](#PLEX_URL) (and authorize once to populate [`PLEX_TOKEN`](#PLEX_TOKEN)), and/or
- [`JELLY_URL`](#JELLY_URL) + [`JELLY_API_KEY`](#JELLY_API_KEY)

The application will try to refresh **all libraries** on the configured server(s).

If you want to only refresh a specific library, set the matching `*_URL_OVERRIDE` to `true` and set the matching `*_URL` to the exact refresh endpoint for that one library.

### Plex override (`PLEX_URL_OVERRIDE`)
The usual config that will refresh everything (JSON):
```json
"app": {
    "PLEX_URL": "http://192.168.1.10:32400",
    "PLEX_URL_OVERRIDE": false
}
```

With `PLEX_URL_OVERRIDE` turned on for only scanning 1 library (JSON):
```json
"app": {
    "PLEX_URL": "http://192.168.1.10:32400/library/sections/1/refresh",
    "PLEX_URL_OVERRIDE": true
}
```

YAML equivalent:
```yaml
app:
    PLEX_URL: "http://192.168.1.10:32400/library/sections/1/refresh"
    PLEX_URL_OVERRIDE: true
```

Where `1` in `/library/sections/1/refresh` is the library key you want to refresh. You can find the library key by running `curl http://<YOUR_SERVER_IP>:32400/library/sections` and looking for the `key="X"` in the output.

### Jellyfin override (`JELLY_URL_OVERRIDE`)
The usual config that will refresh everything (JSON):
```json
"app": {
    "JELLY_URL": "http://192.168.1.10:8096",
    "JELLY_URL_OVERRIDE": false
}
```

With `JELLY_URL_OVERRIDE` turned on for only scanning 1 library (JSON):
```json
"app": {
    "JELLY_URL": "http://192.168.1.10:8096/Items/123456abcdef/Refresh?Recursive=true",
    "JELLY_API_KEY": "blablablablablablabla",
    "JELLY_URL_OVERRIDE": true
}
```

YAML equivalent:
```yaml
app:
    JELLY_URL: "http://192.168.1.10:8096/Items/123456abcdef/Refresh?Recursive=true"
    JELLY_API_KEY: "blablablablablablabla"
    JELLY_URL_OVERRIDE: true
```

Where `123456abcdef` in `/Items/123456abcdef/Refresh?Recursive=true` is the ID of the library you want to refresh. You can find the ID by running `curl http://<YOUR_SERVER_IP>:8096/Users/<USER_ID>/Views?api_key=<YOUR_API_KEY>` and looking for `Id` in the output. You can find your `USER_ID` by running `curl http://<YOUR_SERVER_IP>:8096/Users?api_key=<YOUR_API_KEY>` and looking for `Id` in the output.

---

## How to blacklist entire seasons or just specific episodes

This is great for when you want to skip downloading certain seasons or episodes from a series you are watching. An example use case is that you only want the simulcast season of One Piece and want to skip all the other seasons.

The examples below use [`cr_monitor_series_id`](#cr_monitor_series_id), but the same rules apply to all other monitor maps ([`hidive_monitor_series_id`](#hidive_monitor_series_id), [`adn_monitor_series_id`](#adn_monitor_series_id), [`zlo_cr_monitor_series_id`](#zlo_cr_monitor_series_id), [`zlo_hidive_monitor_series_id`](#zlo_hidive_monitor_series_id), [`zlo_adn_monitor_series_id`](#zlo_adn_monitor_series_id), [`zlo_disneyplus_monitor_series_id`](#zlo_disneyplus_monitor_series_id), [`zlo_amazon_monitor_series_id`](#zlo_amazon_monitor_series_id)).

The general format (JSON):
```json
"cr_monitor_series_id": {
    "series_id": {
        "season_id": {
            "blacklists": [
                "*",
                "episode_num",
                "episode_num_start-episode_num_end"
            ],
            "season_override": "2",
            "dub_overrides": [
                "eng",
                "zho"
            ],
            "sub_overrides": [
                "en",
                "de"
            ]
        }
    }
}
```

YAML equivalent:
```yaml
cr_monitor_series_id:
    series_id:
        season_id:
            blacklists:
                - "*"
                - "episode_num"
                - "episode_num_start-episode_num_end"
            season_override: "2"
            dub_overrides:
                - "eng"
                - "zho"
            sub_overrides:
                - "en"
                - "de"
```

What each `blacklists` entry means:
- `"*"`: all other blacklist entries are ignored, since this blacklists every episode in the season (wildcard).
- `"episode_num"`: that specific episode number is blacklisted (for example, `"3"` blacklists episode 3).
- `"episode_num_start-episode_num_end"`: all episodes in that range, inclusive (for example, `"1-3"` blacklists episodes 1, 2, and 3).

`season_override` changes the season number used in the filename when the source has it wrong (for example, service says `S03E01` but you want `S01E01`). It does not change the actual download command, only how the file is named and organized.  
`dub_overrides` and `sub_overrides` replace the per-service `dubLang` and `dlsubs` for that one season.

You would blacklist an entire season like this (JSON):
```json
{
    "cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": "*"
            }
        },
        "GT00362335": {
            "GS00362336JAJP": {
                "blacklists": "*"
            }
        }
    }
}
```

Where `GYE5CQNJ2` and `GS00362336JAJP` are the season IDs you want to blacklist inside series `GQWH0M1J3` and `GT00362335`. This will skip downloading every episode of those seasons.

You would blacklist a single episode from a season like this (JSON):
```json
{
    "cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": ["3"]
            }
        },
        "GT00362335": {
            "GS00362336JAJP": {
                "blacklists": ["6"]
            }
        }
    }
}
```

Or a range of episodes from a season like this (JSON):
```json
{
    "cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": ["1-3"]
            }
        },
        "GT00362335": {
            "GS00362336JAJP": {
                "blacklists": ["1-5"]
            }
        }
    }
}
```

`blacklists` is a list, so you can combine as many entries as you want (JSON):
```json
{
    "cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": ["*"]
            },
            "blablabla": {
                "blacklists": ["4", "6-8"]
            },
            "blablablaaa": {
                "blacklists": ["1-3"]
            }
        },
        "GT00362335": {
            "GS00362336JAJP": {
                "blacklists": ["*"]
            }
        }
    }
}
```

Blacklisting a season or episode still generates the queue data for the series. All this does is set `episode_skip` to `true`, and the download process checks that flag and either skips or downloads accordingly.

---

## Environment variables

These are environment variables you can set in `docker-compose.yaml` under the `environment` section. They are not in the config file.

### <a id="UID"></a>UID

| Default | Description |
| :--- | :--- |
| `1000` | User ID that mdnx-auto-dl will run as. |

YAML:
```yaml
environment:
    - UID=1000
```

### <a id="GID"></a>GID

| Default | Description |
| :--- | :--- |
| `1000` | Group ID that mdnx-auto-dl will run as. |

YAML:
```yaml
environment:
    - GID=1000
```

### <a id="TZ"></a>TZ

| Default | Description |
| :--- | :--- |
| `America/New_York` | Timezone for the container. Set to your local timezone from the "TZ identifier" column [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). |

YAML:
```yaml
environment:
    - TZ=America/New_York
```

### <a id="CONFIG_FILE"></a>CONFIG_FILE

| Default | Description |
| :--- | :--- |
| auto-detected from `/app/appdata/config/config.json`, then `/app/appdata/config/config.yaml`, then `/app/appdata/config/config.yml`. Falls back to `/app/appdata/config/config.json` if none exist. | Override the config file path inside the container. Use this if your config file lives somewhere other than the default location, or if you want to force a specific format. |

YAML:
```yaml
environment:
    - CONFIG_FILE=/app/appdata/config/config.yaml
```

### <a id="QUEUE_DB_FILE"></a>QUEUE_DB_FILE

| Default | Description |
| :--- | :--- |
| `appdata/config/queue.db` | Path to the SQLite queue database. Override this if you want the queue file in a different location. |

YAML:
```yaml
environment:
    - QUEUE_DB_FILE=appdata/config/queue.db
```

### <a id="BENTO4_URL"></a>BENTO4_URL

| Default | Description |
| :--- | :--- |
| `https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/bento4.zip` | URL for downloading `bento4.zip` if neither the file itself nor the extracted folder already exists. |

YAML:
```yaml
environment:
    - BENTO4_URL=https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/bento4.zip
```

### <a id="MDNX_URL"></a>MDNX_URL

| Default | Description |
| :--- | :--- |
| `https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/mdnx.zip` | URL for downloading `mdnx.zip` if neither the file itself nor the extracted folder already exists. |

YAML:
```yaml
environment:
    - MDNX_URL=https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/mdnx.zip
```

### <a id="SHAKA_URL"></a>SHAKA_URL

| Default | Description |
| :--- | :--- |
| `https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/shaka_packager.zip` | URL for downloading `shaka_packager.zip` if neither the file itself nor the extracted binary already exists. |

YAML:
```yaml
environment:
    - SHAKA_URL=https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/shaka_packager.zip
```

### <a id="FREEZE"></a>FREEZE

| Default | Description |
| :--- | :--- |
| `false` | When `true`, the entrypoint sets up dependencies but does **not** start `app.py`. The container stays alive but idle. Useful for debugging or for getting a shell inside a fully prepared image. |

YAML:
```yaml
environment:
    - FREEZE=true
```

### <a id="REMOTE_SPECIALS_URL"></a>REMOTE_SPECIALS_URL

| Default | Description |
| :--- | :--- |
| `https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/dev/remote-specials.yaml` | HTTPS URL to a YAML file listing episodes that the per-service special episode detection misses. Fetched once per main loop pass. Each matched episode is dropped at parse time, just like a real special, so the rest of the episode numbers shift up. Set to `false` to turn the feature off with no network calls. The file format is documented inside `remote-specials.yaml` at the repo root, and the [get-started guide](get-started.md#remote-specials-override) walks through how to add an entry. |

YAML:
```yaml
environment:
    - REMOTE_SPECIALS_URL=https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/dev/remote-specials.yaml
```
