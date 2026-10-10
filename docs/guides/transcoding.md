# How-to: Transcode finished files with ffmpeg

Transcoding runs your own `ffmpeg` command on a finished episode. Use it to re-encode the video to a smaller codec, drop tracks you do not want, burn in subtitles, or anything else a single ffmpeg command can do.

Transcoding runs after a download finishes and, if you also use [TrackForge](trackforge.md), after TrackForge. It works on the file in the temp directory before the file is moved into your library, so the copy that lands in your library is the processed one. If the ffmpeg command fails (non-zero exit), mdnx-auto-dl leaves the file where it is and retries the episode on the next loop. If TrackForge is enabled and fails on a file, the transcode is skipped and the episode is retried, so TrackForge always gets first crack at the file.

`ffmpeg` (and `ffprobe`) ship inside the container image, so there is nothing extra to install. The temp file is always an `.mkv`, and the transcoded result replaces it, so keep your output as mkv.

---

## Turn it on for a service

Transcoding config lives under the top-level `extra_features` key, in `extra_features.services.<service>.transcoding`. Each service is keyed by name, using the same names as [`destinations`](../config-options.md#destinations): `mdnx-crunchyroll`, `mdnx-hidive`, `mdnx-adn`, `cdl-crunchyroll`, `cdl-hidive`, `cdl-adn`, `cdl-disney`, `cdl-netflix`, `cdl-amazon`.

A service does nothing until you set `enabled` to `true` and give it a non-empty `ffmpeg_command`. Services with no entry, or with `enabled: false`, are left untouched.

JSON:
```json
"extra_features": {
    "services": {
        "cdl-crunchyroll": {
            "transcoding": {
                "enabled": true,
                "ffmpeg_command": "ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}"
            }
        }
    }
}
```
YAML:
```yaml
extra_features:
    services:
        cdl-crunchyroll:
            transcoding:
                enabled: true
                ffmpeg_command: "ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}"
```

- [`enabled`](../config-options.md#transcoding-enabled): when `true`, run the `ffmpeg_command` on every finished file for this service.
- [`ffmpeg_command`](../config-options.md#transcoding-ffmpeg_command): the full ffmpeg command to run. An empty string means it does nothing, even when `enabled` is `true`.

> [!NOTE]
> The same service entry can also hold a [`trackforge`](trackforge.md) block. The two features are independent: you can turn on one, the other, or both. When both are on, TrackForge runs first and the transcode runs on its output.

---

## Write the command

The `ffmpeg_command` is the whole command, starting with `ffmpeg`. It must contain two placeholders:

- `{input}`: the downloaded file. mdnx-auto-dl fills this in with the real path at run time.
- `{output}`: where ffmpeg writes the result. mdnx-auto-dl fills this in, runs the command, then swaps the output file in for the input so the transfer step uses the processed file.

Both placeholders are required. The command is checked when your config loads, so a command missing `{input}` or `{output}` stops the container on startup.

Some examples:

| Command | Result |
| :--- | :--- |
| `ffmpeg -i {input} -c:v libx265 -crf 24 -c:a copy -c:s copy {output}` | Re-encode the video to HEVC at CRF 24, keep audio and subtitles as-is. |
| `ffmpeg -i {input} -map 0 -c copy -sn {output}` | Keep everything but strip the subtitle tracks, no re-encoding. |
| `ffmpeg -i {input} -c:v copy -c:a aac -b:a 192k -c:s copy {output}` | Keep the video, re-encode audio to 192k AAC. |

Because the result replaces the original mkv, keep the container as mkv. Point `{output}` at the placeholder as shown above and let mdnx-auto-dl handle the real paths; it writes to a temporary file next to the input and only swaps it in once ffmpeg exits cleanly.

---

## Use a different command for one season

To run a different command on a single season, set `ffmpeg_command` on that season in the service's monitor map. It only has an effect when transcoding is enabled for the service. See [Blacklists & per-season overrides](series-overrides.md#transcode-one-season-differently).

---

For the full list of transcoding options and their defaults, see the [Transcoding reference](../config-options.md#transcoding).
