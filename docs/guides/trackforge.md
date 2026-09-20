# How-to: Re-encode audio with TrackForge

[TrackForge](https://github.com/HyperNylium/TrackForge) rebuilds the audio tracks of a finished episode from a profile you choose. Use it to keep the original track, re-encode to another codec, downmix to a channel layout, or run an Even-Out-Sound dialogue-forward pass so quiet dialogue is easier to hear.

TrackForge runs after a download finishes and before the file is moved into your library. It works on the file in the temp directory, in place, so the copy that lands in your library is the processed one. If TrackForge fails on a file, mdnx-auto-dl leaves the file where it is and retries the episode on the next loop.

The TrackForge binary ships inside the container image, so there is nothing extra to install. Make sure you are on a recent image. If you enable TrackForge for a service but the image does not have the binary, the container stops on startup and asks you to pull or rebuild a newer image.

---

## Turn it on for a service

TrackForge config lives under the top-level `extra_features` key, in `extra_features.trackforge.services`. Each entry is keyed by service name, using the same names as [`destinations`](../config-options.md#destinations): `mdnx-crunchyroll`, `mdnx-hidive`, `mdnx-adn`, `cdl-crunchyroll`, `cdl-hidive`, `cdl-adn`, `cdl-disney`, `cdl-netflix`, `cdl-amazon`.

A service does nothing until you set `enabled` to `true` and give it a non-empty `profile`. Services with no entry, or with `enabled: false`, are left untouched.

JSON:
```json
"extra_features": {
    "trackforge": {
        "services": {
            "cdl-crunchyroll": {
                "enabled": true,
                "profile": "ORIG, EOS:2.0",
                "workers": 1,
                "muxer": "auto"
            }
        }
    }
}
```
YAML:
```yaml
extra_features:
    trackforge:
        services:
            cdl-crunchyroll:
                enabled: true
                profile: "ORIG, EOS:2.0"
                workers: 1
                muxer: "auto"
```

- [`enabled`](../config-options.md#trackforge-enabled): when `true`, run TrackForge on every finished file for this service.
- [`profile`](../config-options.md#trackforge-profile): the tracks TrackForge builds. An empty string means it does nothing, even when `enabled` is `true`.
- [`workers`](../config-options.md#trackforge-workers): how many audio tracks to encode at once within a file. Must be `1` or higher.
- [`muxer`](../config-options.md#trackforge-muxer): `auto`, `ffmpeg`, or `mkvmerge`. `auto` picks mkvmerge for mkv output when it is available and ffmpeg otherwise.

---

## Write a profile

A profile is a comma-separated list of items. Each item turns every source audio track into one output track, in the order you list them. An item is a token with an optional channel layout after a colon.

- `ORIG`: copy the source track unchanged, with no re-encoding.
- A codec: one of `AAC`, `AC3`, `EAC3`, `DTS`, `OPUS`, `FLAC`, or `WAV` (`PCM` is accepted as an alias for `WAV`). Re-encodes the track to that codec.
- `EOS` or `EOS+`: run TrackForge's Even-Out-Sound dialogue-forward downmix, then encode with the default codec (`AC3`). Write it as `EOS-<codec>`, for example `EOS-EAC3`, to force a specific codec instead of the default.
- Channel layout (optional): add `:1.0`, `:2.0`, `:5.1`, or `:7.1` to set the output layout. Leave it off to keep the source layout.

Some common profiles:

| Profile | Result |
| :--- | :--- |
| `ORIG` | Keep the original track as-is. |
| `AAC:2.0` | Replace it with a single stereo AAC track. |
| `ORIG, EOS:2.0` | Keep the original and add a stereo Even-Out-Sound track. |
| `ORIG, EOS-EAC3:5.1` | Keep the original and add a 5.1 Even-Out-Sound track encoded as EAC3. |

The profile is checked when your config loads, so a malformed profile stops the container on startup. See the [TrackForge project](https://github.com/HyperNylium/TrackForge) for the full profile reference.

---

## Use a different profile for one season

To run a different profile on a single season, set `trackforge_profile` on that season in the service's monitor map. It uses the exact same profile format and only has an effect when TrackForge is enabled for the service. See [Blacklists & per-season overrides](series-overrides.md#override-the-trackforge-profile-per-season).

---

For the full list of TrackForge options and their defaults, see the [TrackForge reference](../config-options.md#trackforge).
