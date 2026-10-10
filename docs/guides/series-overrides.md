# How-to: Blacklists & per-season overrides

Inside each monitor map you can attach settings to a specific season of a series: skip episodes you do not want, renumber a season, shift the episode numbers, change which dubs/subs are downloaded for just that season, send that season to a different folder with a different folder structure, run a different TrackForge profile, or run a different ffmpeg transcode on that season. You can also set a couple of overrides at the series level, above the seasons: a `series_name` and a release `year`.

The examples below use `mdnx_cr_monitor_series_id`, but the same rules apply to every monitor map: the aniDL maps `mdnx_*` <sup>[1](../config-options.md#mdnx_cr_monitor_series_id "mdnx_cr_monitor_series_id") [2](../config-options.md#mdnx_hidive_monitor_series_id "mdnx_hidive_monitor_series_id") [3](../config-options.md#mdnx_adn_monitor_series_id "mdnx_adn_monitor_series_id")</sup> and the CardinalDL maps `cdl_*` <sup>[1](../config-options.md#cdl_cr_monitor_series_id "cdl_cr_monitor_series_id") [2](../config-options.md#cdl_hidive_monitor_series_id "cdl_hidive_monitor_series_id") [3](../config-options.md#cdl_adn_monitor_series_id "cdl_adn_monitor_series_id") [4](../config-options.md#cdl_disney_monitor_series_id "cdl_disney_monitor_series_id") [5](../config-options.md#cdl_netflix_monitor_series_id "cdl_netflix_monitor_series_id") [6](../config-options.md#cdl_amazon_monitor_series_id "cdl_amazon_monitor_series_id")</sup>.

These maps are **top-level** keys, not under `app`.

---

## The general format

```json
"mdnx_cr_monitor_series_id": {
    "series_id": {
        "series_name": "My Show",
        "year": "2021",
        "season_id": {
            "blacklists": [
                "*",
                "episode_num",
                "episode_num_start-episode_num_end"
            ],
            "season_override": "2",
            "episode_offset": 0,
            "dub_overrides": ["eng", "zho"],
            "sub_overrides": ["en", "de"],
            "dir_override": "/data/special-shows",
            "folder_structure_override": "${seriesTitle}/${seriesTitle} - S${seasonPadded}E${episodePadded}",
            "trackforge_profile": "ORIG, EOS:2.0",
            "ffmpeg_command": "ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}"
        }
    }
}
```

YAML:
```yaml
mdnx_cr_monitor_series_id:
    series_id:
        series_name: "My Show"
        year: "2021"
        season_id:
            blacklists:
                - "*"
                - "episode_num"
                - "episode_num_start-episode_num_end"
            season_override: "2"
            episode_offset: 0
            dub_overrides:
                - "eng"
                - "zho"
            sub_overrides:
                - "en"
                - "de"
            dir_override: "/data/special-shows"
            folder_structure_override: "${seriesTitle}/${seriesTitle} - S${seasonPadded}E${episodePadded}"
            trackforge_profile: "ORIG, EOS:2.0"
            ffmpeg_command: "ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}"
```

A series maps to one or more seasons. `series_name` and `year` are optional keys that sit at the series level, next to the seasons, and apply to the whole series. Every other key under a series is treated as a season ID. Everything inside a season is optional too, and a season with an empty `{}` is just monitored normally.

Series-level overrides:

- **`series_name`**: set this series to a different name instead of the name the service reports.
- **`year`**: override the release year used when filing the series. Handy when the service has the wrong year or leaves it blank.

Per-season overrides:

- **`blacklists`**: skip episodes (see below).
- **`season_override`**: change the season number used in the file name when the source has it wrong (for example, the service says `S03E01` but you want `S01E01`). It only changes how the file is named and organized, not the download command.
- **`episode_offset`**: shift this season's episode numbers by a whole number (see below). Can be negative. Specials are left alone.
- **`dub_overrides`** / **`sub_overrides`**: replace the per-service dub and subtitle languages (aniDL `dubLang` / CardinalDL `dublang`, and `dlsubs`) for that one season.
- **`dir_override`**: save this season under a different base folder instead of the service `dir` from `destinations`. When it is not set, the global `dir` is used. This lets you send one series somewhere else without changing the global destination.
- **`folder_structure_override`**: use a different folder and file name template for this season instead of the service `folder_structure` from `destinations`. When it is not set, the global `folder_structure` is used. It uses the same variables as `folder_structure` (see [organizing files](organizing-files.md)). `dir_override` and `folder_structure_override` are independent, so you can set just one.
- **`trackforge_profile`**: run a different TrackForge [`profile`](../config-options.md#trackforge-profile) on this season instead of the service profile. Only has an effect when [TrackForge](../config-options.md#trackforge) is enabled for the service. When it is not set, the service-level profile is used. Uses the same profile format as the service option.
- **`ffmpeg_command`**: run a different [transcode](../config-options.md#transcoding) command on this season instead of the service command. Only has an effect when transcoding is enabled for the service. When it is not set, the service-level command is used. Uses the same `{input}`/`{output}` format as the service option.

---

## Blacklists

`blacklists` is a list. Each entry is one of:

- `"*"`: blacklist every episode in the season (whole-season skip). All other entries are ignored when this is present.
- `"N"`: blacklist that specific episode number (for example, `"3"` skips episode 3).
- `"N-M"`: blacklist a closed range, inclusive (for example, `"1-3"` skips episodes 1, 2, and 3).
- `"N-*"`: open-ended range from episode N to the end of the season, inclusive (for example, `"5-*"` skips episode 5 and everything after it). Handy for ongoing seasons where you do not know the final episode number.
- `"*-N"`: open-ended range from the start of the season up to episode N, inclusive (for example, `"*-4"` skips episodes 1 through 4).

> [!NOTE]
> `"*-*"` is not a valid range and is ignored. Use plain `"*"` to blacklist a whole season.

Blacklisting still generates the queue data for the series. It just sets `episode_skip` to `true`, and the download step skips those episodes.

### Skip whole seasons

Great for when you only want the simulcast season of a long series and want to skip all the others:
```json
{
    "mdnx_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": ["*"]
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
YAML:
```yaml
mdnx_cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            blacklists: ["*"]
    GT00362335:
        GS00362336JAJP:
            blacklists: ["*"]
```
Here `GYE5CQNJ2` and `GS00362336JAJP` are the season IDs to skip inside series `GQWH0M1J3` and `GT00362335`.

### Skip specific episodes or ranges

```json
{
    "mdnx_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": ["3"]
            },
            "some_other_season": {
                "blacklists": ["1-3"]
            },
            "yet_another_season": {
                "blacklists": ["4", "6-8"]
            }
        }
    }
}
```
YAML:
```yaml
mdnx_cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            blacklists:
                - "3"
        some_other_season:
            blacklists:
                - "1-3"
        yet_another_season:
            blacklists:
                - "4"
                - "6-8"
```

### Keep only part of an ongoing season

Skip everything at or below episode 3 and everything at or above episode 6, keeping only episodes 4 and 5:
```json
{
    "mdnx_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "blacklists": ["*-3", "6-*"]
            }
        }
    }
}
```
YAML:
```yaml
mdnx_cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            blacklists:
                - "*-3"
                - "6-*"
```

---

## Overriding the season number

When a service numbers a season differently from how you want it filed, use `season_override`.  
The example below files the season's episodes as season 1 regardless of what the source says:
```json
{
    "mdnx_cr_monitor_series_id": {
        "GT00362335": {
            "GS00362336JAJP": {
                "season_override": "1"
            }
        }
    }
}
```
YAML:
```yaml
mdnx_cr_monitor_series_id:
    GT00362335:
        GS00362336JAJP:
            season_override: "1"
```

## Offsetting episode numbers

`episode_offset` shifts this season's episode numbers by a whole number. It changes the episode number used when the file is named and filed, not the download itself. Use a negative number to count down or a positive number to count up. Specials are left alone.

This is handy when a service splits one continuous run across more than one season and restarts the episode numbers each time. For example, Netflix lists Steel Ball Run (JoJo's Bizarre Adventure) as two seasons: the first has only episode 1, and the second picks the story back up but numbers its episodes from 1 again. Filing both under the same season with `season_override` would land two "episode 1" files in one folder, so adding `episode_offset: 1` to the second season shifts it to episode 2 and up and it continues the first cleanly:
```json
{
    "cdl_netflix_monitor_series_id": {
        "82116553": {
            "series_name": "JoJo's Bizarre Adventure",
            "81595018": {
                "season_override": "6"
            },
            "82181513": {
                "episode_offset": 1,
                "season_override": "6"
            }
        }
    }
}
```
YAML:
```yaml
cdl_netflix_monitor_series_id:
    "82116553":
        series_name: "JoJo's Bizarre Adventure"
        "81595018":
            season_override: "6"
        "82181513":
            episode_offset: 1
            season_override: "6"
```

Here Netflix season `81595018` keeps its single episode 1, and season `82181513` starts at episode 2, so season 6 reads as episodes 1, 2, 3, and so on.

## Overriding the series name and year

`series_name` and `year` sit at the series level, next to the seasons, and apply to the whole series. Use them when the service reports a name or release year you do not want on disk. `series_name` changes the folder and file names and the name shown in notifications; `year` changes the release year used when filing the series.

> [!NOTE]
> The series name and year are frozen once a series is in the queue. mdnx-auto-dl records them the first time it adds the series and keeps them across queue refreshes, even if the service later reports a different name or year. A `series_name` or `year` override here always wins, so this is how you correct the name or year of a series that is already in the queue.
```json
{
    "mdnx_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "series_name": "My Show",
            "year": "2021",
            "GYE5CQNJ2": {}
        }
    }
}
```
YAML:
```yaml
mdnx_cr_monitor_series_id:
    GQWH0M1J3:
        series_name: "My Show"
        year: "2021"
        GYE5CQNJ2: {}
```

Here `GYE5CQNJ2` is still a season of the series. `series_name` and `year` are the only keys read as series-level settings; every other key under the series ID is read as a season.

## Overriding dubs and subs per season

`dub_overrides` and `sub_overrides` replace the service's normal dub and subtitle languages for that one season only.  
This is useful when a specific season has a dub the rest of the series does not:
```json
{
    "mdnx_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "dub_overrides": ["eng", "jpn"],
                "sub_overrides": ["en"]
            }
        }
    }
}
```
YAML:
```yaml
mdnx_cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            dub_overrides:
                - "eng"
                - "jpn"
            sub_overrides:
                - "en"
```

Use the same language code format as the service's own dub/subtitle settings: ISO 639-3 like `jpn`/`eng` for aniDL services (`dubLang` / `dlsubs`), and CardinalDL's two-letter codes like `JP`/`EN` for CardinalDL services (`dublang` / `dlsubs`). For CardinalDL, `sub_overrides` entries can also carry a subtitle variant tag like `EN:cc`, `EN:full`, or `EN:both`.

## Override the TrackForge profile per season

`trackforge_profile` runs a different [TrackForge](../config-options.md#trackforge) profile on one season instead of the service profile. It only does anything when TrackForge is enabled for that service. When it is not set, the season uses the service-level profile.  
The example below keeps the original tracks for this one season instead of whatever the service profile does:
```json
{
    "cdl_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "trackforge_profile": "ORIG"
            }
        }
    }
}
```
YAML:
```yaml
cdl_cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            trackforge_profile: "ORIG"
```

The profile uses the exact same format as the service [`profile`](../config-options.md#trackforge-profile) option, so `ORIG`, `AAC:2.0`, and `ORIG, EOS:2.0` all work here too.

## Transcode one season differently

`ffmpeg_command` runs a different [transcode](../config-options.md#transcoding) command on one season instead of the service command. It only does anything when transcoding is enabled for that service. When it is not set, the season uses the service-level command.  
The example below re-encodes just this one season to HEVC:
```json
{
    "cdl_cr_monitor_series_id": {
        "GQWH0M1J3": {
            "GYE5CQNJ2": {
                "ffmpeg_command": "ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}"
            }
        }
    }
}
```
YAML:
```yaml
cdl_cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            ffmpeg_command: "ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}"
```

The command uses the exact same `{input}`/`{output}` format as the service [transcoding](../config-options.md#transcoding) option, and both placeholders are required here too. See the [transcoding guide](transcoding.md) for how the command is run.
