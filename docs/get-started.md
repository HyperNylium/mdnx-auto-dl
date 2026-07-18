## Get started (Docker)

mdnx-auto-dl supports two downloaders, and they are interchangeable. You can pick one, or mix them per service (for example ZLO for HiDive and multi-downloader-nx for Crunchyroll).

- **[Get started with multi-downloader-nx](mdnx-get-started.md)** uses the aniDL binary. It needs your own CDM (Widevine or Playready) and the aniDL binary.
- **[Get started with ZLO](zlo-get-started.md)** uses the `zlo7` binary and a signed-in `.zlo7` config folder. No CDM required.

If you want to mix them, follow one guide all the way through, then add the other downloader's binary and provider steps from its guide.

---

## Next steps

Want to set up a specific feature? The [how-to guides](guides/README.md) walk you through each one:

- [Set up notifications](guides/notifications.md) (SMTP, ntfy, Gotify, Discord webhook)
- [Refresh Plex and Jellyfin](guides/media-servers.md) after a download
- [Organize your files](guides/organizing-files.md) with `folder_structure`
- [Blacklists & per-season overrides](guides/series-overrides.md) to skip or retag seasons
- [Configure ZLO downloads](guides/zlo.md) and [multi-downloader-nx](guides/mdnx.md)

For a full list of every option, see the [option reference](config-options.md).

---

## <a id="remote-specials-override"></a>Remote-specials override

Some recap, OVA, or compilation episodes may slip past the per-service detection because the upstream service does not label them in any way the detector can pick up on.  
The override file `remote-specials.yaml` at the root of this repo lists these episodes manually and the running container fetches the file once per loop pass.

If a special episode gets downloaded when it should have been skipped, open a [Special episode issue](https://github.com/HyperNylium/mdnx-auto-dl/issues/new?template=special-episode.yml) with the series ID or name and which episode it is. A link to the episode on the streaming service helps too. I will add it to `remote-specials.yaml` when I can, and every running container picks up the change on its next loop pass (usually within an hour. thx github cache). The matched episode is then dropped at parse time and the rest of the episode numbers shift up.

If you are comfortable editing `remote-specials.yaml` yourself, you can skip the issue and open a PR adding the entry directly under the right downloader and service. The container logs show the upstream `series_id`, season number, and episode number when it parses each episode when the log level is set to `debug`.

If you maintain your own list, set the [`REMOTE_SPECIALS_URL`](config-options.md#REMOTE_SPECIALS_URL) environment variable in `docker-compose.yaml` to point at any HTTPS URL serving a file with the same shape. Set it to `false` to turn the feature off entirely.

For more advanced configuration, see the [how-to guides](guides/README.md) or the full [option reference](config-options.md).
