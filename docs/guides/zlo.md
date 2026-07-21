# How-to: Configure ZLO downloads

ZLO is a separate downloader from multi-downloader-nx. It uses its own `zlo7` binary and its own `.zlo7` config folder, and you sign in through the ZLO GUI (mdnx-auto-dl never logs you in).

This guide covers **tuning** ZLO downloads. 

If you have not mounted the binary and signed-in config folder yet, do that first: see [zlo-get-started.md](../zlo-get-started.md).

---

## Enable a ZLO service

Each ZLO service has its own enable flag and its own monitor map (both live at the top level of the config). Turn on the ones you want in the `app` section:

```json
"app": {
    "ZLO_CR_ENABLED": true,
    "ZLO_HIDIVE_ENABLED": false,
    "ZLO_ADN_ENABLED": false
}
```

Then add the series IDs you want to monitor to the matching map ([`zlo_cr_monitor_series_id`](../config-options.md#zlo_cr_monitor_series_id), [`zlo_hidive_monitor_series_id`](../config-options.md#zlo_hidive_monitor_series_id), [`zlo_adn_monitor_series_id`](../config-options.md#zlo_adn_monitor_series_id)). You can also blacklist seasons/episodes and override dubs/subs per season there. See [Blacklists & per-season overrides](series-overrides.md).

**Enable flags:** [`ZLO_CR_ENABLED`](../config-options.md#ZLO_CR_ENABLED) [`ZLO_HIDIVE_ENABLED`](../config-options.md#ZLO_HIDIVE_ENABLED) [`ZLO_ADN_ENABLED`](../config-options.md#ZLO_ADN_ENABLED)

---

## Tune quality, dubs, and subtitles

Download settings live in the top-level `zlo` section, which has one subsection per service: `crunchyroll`, `hidive`, and `adn`.  
Each subsection takes the same keys. Only set the keys you want to change. Anything you leave out uses its default.

JSON:
```json
"zlo": {
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
zlo:
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

- [`quality`](../config-options.md#zlo-quality): quality string, format `"{resolution}@{codec}"` (for example, `1080p@avc`, `720p@hvc`).
- [`qualityfallback`](../config-options.md#zlo-qualityfallback): when `true`, fall back to the next-best quality if the requested one is missing.
- [`dubLang`](../config-options.md#zlo-dublang): dub language codes you want, using ZLO's own two-letter codes (`JP`, `EN`, `DE`, `FR`, `ES`, ...).
- [`dlsubs`](../config-options.md#zlo-dlsubs): subtitle language codes, same code format as `dubLang`.
- [`forceSubFormat`](../config-options.md#zlo-forcesubformat): force subtitles into `srt`, `ass`, `vtt`, `auto`, or `raw`. Leave `""` to keep the source format.
- [`backup_dubs`](../config-options.md#zlo-backup_dubs): dubs to fall back to if none of your `dubLang` are available.

---

## Paths (advanced)

You normally do not need to touch these. They control where `zlo7` writes files and where it reads your sign-in from.

- [`dlpath`](../config-options.md#zlo-dlpath): where `zlo7` writes the downloaded MKV before mdnx-auto-dl picks it up.
- [`tempPath`](../config-options.md#zlo-temppath): scratch directory for in-progress segments.
- [`configPath`](../config-options.md#zlo-configpath): path to the ZLO `storage.db` that holds your signed-in account. This is inside the config folder you bind-mount.  
  mdnx-auto-dl also reads it on startup to confirm you are signed in.

For the full list of every ZLO option and its default, see the [ZLO per-service options reference](../config-options.md#zlo-per-service-options).
