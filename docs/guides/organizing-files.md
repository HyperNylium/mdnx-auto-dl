# How-to: Organize your files

Where each service saves finished files, and how the folders and file names are laid out, is controlled by the top-level [`destinations`](../config-options.md#destinations) section.  
Every service you enable needs an entry, or the container exits on startup.

Each entry has two keys:
- `dir`: the folder **inside the container** where files are saved. This must match the right side of one of your bind-mounts in `docker-compose.yaml` (for example, `/data/Anime`).
- `folder_structure`: the layout for series, seasons, and episodes under `dir`, built from the variables below.

Valid destination keys: `crunchyroll`, `hidive`, `adn`, `zlo-crunchyroll`, `zlo-hidive`, `zlo-adn`. You only need entries for the services you enable.

JSON:
```json
"destinations": {
    "crunchyroll": {
        "dir": "/data/Anime",
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
```

---

## folder_structure variables

You can use any of these variables in a `folder_structure` template. See the [full variable table](../config-options.md#options-for-folder_structure) in the reference for details and example values.

| Variable | Example | Notes |
| :--- | :--- | :--- |
| `${seriesTitle}` | `Kaiju No. 8` | Sanitized series title. |
| `${season}` / `${seasonPadded}` | `1` / `01` | Season number, unpadded / padded to two digits. |
| `${episode}` / `${episodePadded}` | `1` / `01` | Episode number, unpadded / padded to two digits. |
| `${episodeName}` | `The Man Who Became a Kaiju` | Sanitized episode title. |
| `${serviceLong}` | `Crunchyroll` | Long service name: `Crunchyroll`, `HiDive`, `ADN`. |
| `${serviceShort}` | `CR` | Short service code: `CR`, `HD`, `ADN`. |

`${serviceLong}` and `${serviceShort}` are the same for the aniDL and ZLO variant of a service (both Crunchyroll destinations resolve to `Crunchyroll` / `CR`).

---

## Recipes

**Default layout.** Series folder, season subfolder, `SxxExx` file name:
```txt
${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}
```
```txt
Kaiju No. 8/S1/Kaiju No. 8 - S01E01
```

**Include the episode title** in the file name:
```txt
${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded} - ${episodeName}
```
```txt
Kaiju No. 8/S1/Kaiju No. 8 - S01E01 - The Man Who Became a Kaiju
```

**Separate each service into its own top-level folder**, and tag the file name with where it came from:
```txt
${serviceLong}/${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded} [${serviceShort}]
```
```txt
Crunchyroll/Kaiju No. 8/S1/Kaiju No. 8 - S01E01 [CR]
```

> [!TIP]
> Each service has its own `destinations` entry, so you can also keep services apart just by giving them different `dir` values (for example, Crunchyroll to `/data/Anime`, ADN to `/data/Anime-ADN`) instead of, or in addition to, using `${serviceLong}` in the template.

---

## Changing where files land on your host

The shipped config points every service at `/data/Anime`, which the default `docker-compose.yaml` mounts.  
To save somewhere else on your host, change the **left** side of the bind-mount in `docker-compose.yaml` (for example, `./appdata/data/Anime` to `/mnt/chungus/Anime`) and keep the right side the same.  
If you change the right side (the path inside the container), update the matching `destinations.<service>.dir` too.
