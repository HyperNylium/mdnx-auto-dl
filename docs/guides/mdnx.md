# How-to: Configure multi-downloader-nx (aniDL)

The Crunchyroll, HiDive, and ADN services that go through [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx) (aniDL) share one config block: the top-level `mdnx` section.

Each subsection of `mdnx` maps to a file of the same name in multi-downloader-nx's `config` folder. On startup, mdnx-auto-dl writes whatever you put under a subsection straight into that file, so you can treat a subsection as if you were editing the multi-downloader-nx file directly:

- [`cli-defaults`](../config-options.md#mdnx-cli-defaults) becomes `cli-defaults.yml`
- [`bin-path`](../config-options.md#mdnx-bin-path) becomes `bin-path.yml`
- [`dir-path`](../config-options.md#mdnx-dir-path) becomes `dir-path.yml`

So under `cli-defaults`, anything valid in multi-downloader-nx's `cli-defaults.yml` is valid here, as long as the option's `cli-default Entry` in [multi-downloader-nx's documentation](https://github.com/anidl/multi-downloader-nx/blob/master/docs/DOCUMENTATION.md) is not `NaN`.

You only need to set the keys you want to override. Anything you leave out keeps its default.

> [!NOTE]
> This section only applies to the aniDL versions of Crunchyroll, HiDive, and ADN. The ZLO versions are configured separately.  
> See [Configure ZLO downloads](zlo.md).

---

## Download settings (`cli-defaults`)

This is the subsection you will touch most. It holds the default download settings passed to aniDL.

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

Common keys:
- `q`: quality. `0` means best available.
- `dubLang`: dub languages you want, in order. Uses ISO 639-3 codes (for example, `jpn`, `eng`).
- `dlsubs`: subtitle languages you want.
- `defaultAudio` / `defaultSub`: which track to mark as default in the output file.
- `tsd`: kills active Crunchyroll streaming sessions to avoid the `TOO_MANY_ACTIVE_STREAMS` error. Crunchyroll only, and it will kick anyone currently watching on your account.

To add any other aniDL setting, just add its `cli-defaults.yml` key here.  
See the full defaults and the paths subsections in the [multi-downloader-nx options reference](../config-options.md#multi-downloader-nx-options).

---

## Binary and directory paths (advanced)

The [`bin-path`](../config-options.md#mdnx-bin-path) and [`dir-path`](../config-options.md#mdnx-dir-path) subsections point aniDL at its helper binaries (`ffmpeg`, `ffprobe`, `mkvmerge`, `mp4decrypt`) and working directories. The defaults match what the container ships with, so you only need to change these if you mount your own binaries or move the working directories.
