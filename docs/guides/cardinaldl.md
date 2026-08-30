# How-to: Configure CardinalDL downloads

CardinalDL is a separate downloader from multi-downloader-nx. It uses its own CardinalDL binary and its own `.cardinaldl` config folder, and you sign in through the CardinalDL GUI (mdnx-auto-dl never logs you in).

This guide covers **tuning** CardinalDL downloads. 

If you have not mounted the binary and signed-in config folder yet, do that first: see [cardinaldl-get-started.md](../cardinaldl-get-started.md).

---

## Enable a CardinalDL service

Each CardinalDL service has its own enable flag and its own monitor map (both live at the top level of the config). Turn on the ones you want in the `app` section:

```json
"app": {
    "CDL_CR_ENABLED": true,
    "CDL_HIDIVE_ENABLED": false,
    "CDL_ADN_ENABLED": false,
    "CDL_DISNEY_ENABLED": false,
    "CDL_NETFLIX_ENABLED": false,
    "CDL_AMAZON_ENABLED": false
}
```

Then add the series IDs you want to monitor to the matching map ([`cdl_cr_monitor_series_id`](../config-options.md#cdl_cr_monitor_series_id), [`cdl_hidive_monitor_series_id`](../config-options.md#cdl_hidive_monitor_series_id), [`cdl_adn_monitor_series_id`](../config-options.md#cdl_adn_monitor_series_id), [`cdl_disney_monitor_series_id`](../config-options.md#cdl_disney_monitor_series_id), [`cdl_netflix_monitor_series_id`](../config-options.md#cdl_netflix_monitor_series_id), [`cdl_amazon_monitor_series_id`](../config-options.md#cdl_amazon_monitor_series_id)). You can also blacklist seasons/episodes and override dubs/subs per season there. See [Blacklists & per-season overrides](series-overrides.md).

**Enable flags:** [`CDL_CR_ENABLED`](../config-options.md#CDL_CR_ENABLED) [`CDL_HIDIVE_ENABLED`](../config-options.md#CDL_HIDIVE_ENABLED) [`CDL_ADN_ENABLED`](../config-options.md#CDL_ADN_ENABLED) [`CDL_DISNEY_ENABLED`](../config-options.md#CDL_DISNEY_ENABLED) [`CDL_NETFLIX_ENABLED`](../config-options.md#CDL_NETFLIX_ENABLED) [`CDL_AMAZON_ENABLED`](../config-options.md#CDL_AMAZON_ENABLED)

---

## Tune quality, dubs, and subtitles

Download settings live in the top-level `cardinaldl` section, which has one subsection per service: `crunchyroll`, `hidive`, `adn`, `disney`, `netflix`, and `amazon`.  
Each subsection takes the same keys. Only set the keys you want to change. Anything you leave out uses its default.

JSON:
```json
"cardinaldl": {
    "crunchyroll": {
        "videoquality": "1080p@@sdr",
        "audioquality": "aac@2.0",
        "fallback": true,
        "outputformat": "mkv",
        "dectool": "shaka",
        "dublang": ["JP", "EN"],
        "dlsubs": ["EN"],
        "forcesubformat": "",
        "backup_dubs": []
    }
}
```
YAML:
```yaml
cardinaldl:
    crunchyroll:
        videoquality: "1080p@@sdr"
        audioquality: "aac@2.0"
        fallback: true
        outputformat: "mkv"
        dectool: "shaka"
        dublang:
            - "JP"
            - "EN"
        dlsubs:
            - "EN"
        forcesubformat: ""
        backup_dubs: []
```

- [`videoquality`](../config-options.md#cdl-videoquality): video quality string, format `"{resolution}@{codec}@{range}"` (for example, `1080p@@sdr`, `720p@hevc`, `2160p@hevc@dv`). Use `highest` for the resolution to take the best available.
- [`audioquality`](../config-options.md#cdl-audioquality): audio codec and channel layout, format `"{codec}@{channels}"` (for example, `aac@2.0`, `eac3@5.1`). Prefix a language like `EN:eac3@5.1` and comma-separate to list more than one.
- [`fallback`](../config-options.md#cdl-fallback): when `true`, fall back to the next-best quality if the requested one is missing.
- [`outputformat`](../config-options.md#cdl-outputformat): container for the finished file, `mkv` or `mp4`.
- [`dectool`](../config-options.md#cdl-dectool): decryption tool, `shaka` or `mp4decrypt`.
- [`dublang`](../config-options.md#cdl-dublang): dub language codes you want, using CardinalDL's own two-letter codes (`JP`, `EN`, `DE`, `FR`, `ES`, ...).
- [`dlsubs`](../config-options.md#cdl-dlsubs): subtitle language codes, same codes as `dublang`. Add a variant tag like `EN:cc`, `EN:full`, or `EN:both` to pick a specific subtitle track. The tag also controls what mdnx-auto-dl treats as complete when it checks for missing subs. A bare `EN` accepts any variant. See the [`dlsubs` reference](../config-options.md#cdl-dlsubs) for the full breakdown.
- [`forcesubformat`](../config-options.md#cdl-forcesubformat): force subtitles into `srt`, `ass`, `vtt`, `auto`, `raw`, or `original`. Leave `""` to keep the source format.
- [`backup_dubs`](../config-options.md#cdl-backup_dubs): dubs to fall back to if none of your `dublang` are available.

---

## Paths (advanced)

You normally do not need to touch these. They control where CardinalDL writes files and where it reads your sign-in from.

- [`dlpath`](../config-options.md#cdl-dlpath): where CardinalDL writes the downloaded file before mdnx-auto-dl picks it up.
- [`temppath`](../config-options.md#cdl-temppath): scratch directory for in-progress segments.
- [`configpath`](../config-options.md#cdl-configpath): path to the CardinalDL `storage.db` that holds your signed-in account. This is inside the config folder you bind-mount.  
  mdnx-auto-dl also reads it on startup to confirm you are signed in.

For the full list of every CardinalDL option and its default, see the [CardinalDL per-service options reference](../config-options.md#cardinaldl-per-service-options).
