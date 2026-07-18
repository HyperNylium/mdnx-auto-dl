# How-to: Blacklists & per-season overrides

Inside each monitor map you can attach settings to a specific season of a series: skip episodes you do not want, renumber a season, or change which dubs/subs are downloaded for just that season.

The examples below use [`cr_monitor_series_id`](../config-options.md#cr_monitor_series_id), but the same rules apply to every monitor map: [`hidive_monitor_series_id`](../config-options.md#hidive_monitor_series_id), [`adn_monitor_series_id`](../config-options.md#adn_monitor_series_id), [`zlo_cr_monitor_series_id`](../config-options.md#zlo_cr_monitor_series_id), [`zlo_hidive_monitor_series_id`](../config-options.md#zlo_hidive_monitor_series_id), and [`zlo_adn_monitor_series_id`](../config-options.md#zlo_adn_monitor_series_id).

These maps are **top-level** keys, not under `app`.

---

## The general format

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
            "dub_overrides": ["eng", "zho"],
            "sub_overrides": ["en", "de"]
        }
    }
}
```

YAML:
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

Everything under a season is optional. A season with an empty `{}` is just monitored normally.

- **`blacklists`**: skip episodes (see below).
- **`season_override`**: change the season number used in the file name when the source has it wrong (for example, the service says `S03E01` but you want `S01E01`). It only changes how the file is named and organized, not the download command.
- **`dub_overrides`** / **`sub_overrides`**: replace the per-service `dubLang` and `dlsubs` for that one season.

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
YAML:
```yaml
cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            blacklists: "*"
    GT00362335:
        GS00362336JAJP:
            blacklists: "*"
```
Here `GYE5CQNJ2` and `GS00362336JAJP` are the season IDs to skip inside series `GQWH0M1J3` and `GT00362335`.

### Skip specific episodes or ranges

```json
{
    "cr_monitor_series_id": {
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
cr_monitor_series_id:
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
    "cr_monitor_series_id": {
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
cr_monitor_series_id:
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
    "cr_monitor_series_id": {
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
cr_monitor_series_id:
    GT00362335:
        GS00362336JAJP:
            season_override: "1"
```

## Overriding dubs and subs per season

`dub_overrides` and `sub_overrides` replace the service's normal `dubLang` / `dlsubs` for that one season only.  
This is useful when a specific season has a dub the rest of the series does not:
```json
{
    "cr_monitor_series_id": {
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
cr_monitor_series_id:
    GQWH0M1J3:
        GYE5CQNJ2:
            dub_overrides:
                - "eng"
                - "jpn"
            sub_overrides:
                - "en"
```

Use the same language code format as the service's own `dubLang` / `dlsubs` (ISO 639-3 like `jpn`/`eng` for aniDL services, ZLO's two-letter codes like `JP`/`EN` for ZLO services).
