# How-to: Configure CardinalDL downloads

CardinalDL is a separate downloader from multi-downloader-nx. It uses its own `cardinaldl` binary and its own `.cardinaldl` config folder, and you sign in through the CardinalDL GUI (mdnx-auto-dl never logs you in).

This guide covers **tuning** CardinalDL downloads. 

If you have not mounted the binary and signed-in config folder yet, do that first: see [cardinaldl-get-started.md](../cardinaldl-get-started.md).

---

## Enable a CardinalDL service

Each CardinalDL service has its own enable flag and its own monitor map (both live at the top level of the config). Turn on the ones you want in the `app` section:

```json
"app": {
    "CDL_CR_ENABLED": true,
    "CDL_HIDIVE_ENABLED": false,
    "CDL_ADN_ENABLED": false
}
```

Then add the series IDs you want to monitor to the matching map ([`cdl_cr_monitor_series_id`](../config-options.md#cdl_cr_monitor_series_id), [`cdl_hidive_monitor_series_id`](../config-options.md#cdl_hidive_monitor_series_id), [`cdl_adn_monitor_series_id`](../config-options.md#cdl_adn_monitor_series_id)). You can also blacklist seasons/episodes and override dubs/subs per season there. See [Blacklists & per-season overrides](series-overrides.md).

**Enable flags:** [`CDL_CR_ENABLED`](../config-options.md#CDL_CR_ENABLED) [`CDL_HIDIVE_ENABLED`](../config-options.md#CDL_HIDIVE_ENABLED) [`CDL_ADN_ENABLED`](../config-options.md#CDL_ADN_ENABLED)

---

## Tune quality, dubs, and subtitles

Download settings live in the top-level `cardinaldl` section, which has one subsection per service: `crunchyroll`, `hidive`, and `adn`.  
Each subsection takes the same keys. Only set the keys you want to change. Anything you leave out uses its default.

JSON:
```json
"cardinaldl": {
    "crunchyroll": {
        "quality": "1080p@avc",
        "qualityfallback": true,
        "dubLang": ["JP", "EN"],
        "dlsubs": ["EN"],
        "forceSubFormat": "",
        "backup_dubs": []
    }
}
```
YAML:
```yaml
cardinaldl:
    crunchyroll:
        quality: "1080p@avc"
        qualityfallback: true
        dubLang:
            - "JP"
            - "EN"
        dlsubs:
            - "EN"
        forceSubFormat: ""
        backup_dubs: []
```

- [`quality`](../config-options.md#cdl-quality): quality string, format `"{resolution}@{codec}"` (for example, `1080p@avc`, `720p@hvc`).
- [`qualityfallback`](../config-options.md#cdl-qualityfallback): when `true`, fall back to the next-best quality if the requested one is missing.
- [`dubLang`](../config-options.md#cdl-dublang): dub language codes you want, using CardinalDL's own two-letter codes (`JP`, `EN`, `DE`, `FR`, `ES`, ...).
- [`dlsubs`](../config-options.md#cdl-dlsubs): subtitle language codes, same code format as `dubLang`.
- [`forceSubFormat`](../config-options.md#cdl-forcesubformat): force subtitles into `srt`, `ass`, `vtt`, `auto`, or `raw`. Leave `""` to keep the source format.
- [`backup_dubs`](../config-options.md#cdl-backup_dubs): dubs to fall back to if none of your `dubLang` are available.

---

## Paths (advanced)

You normally do not need to touch these. They control where `cardinaldl` writes files and where it reads your sign-in from.

- [`dlpath`](../config-options.md#cdl-dlpath): where `cardinaldl` writes the downloaded MKV before mdnx-auto-dl picks it up.
- [`tempPath`](../config-options.md#cdl-temppath): scratch directory for in-progress segments.
- [`configPath`](../config-options.md#cdl-configpath): path to the CardinalDL `storage.db` that holds your signed-in account. This is inside the config folder you bind-mount.  
  mdnx-auto-dl also reads it on startup to confirm you are signed in.

For the full list of every CardinalDL option and its default, see the [CardinalDL per-service options reference](../config-options.md#cardinaldl-per-service-options).
