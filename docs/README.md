# MDNX-auto-dl

[![Discord Server](https://discord.com/api/guilds/789034812799320074/widget.png?style=banner2)](https://discord.gg/XAAfYJ5ABk)

## Legal Warning
This application is not endorsed by or affiliated with *Crunchyroll*, *Hidive* or *AnimationDigitalNetwork*. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the *Terms of Service* between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

# What is this?
MDNX-auto-dl is a free and open-source headless orchestrator that automatically downloads new episodes from Crunchyroll, HiDive and AnimationDigitalNetwork (ADN) as they are released. It is not a GUI app.  
Instead of downloading anything itself, it manages the tools that do, [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx) and/or ZLO7, and handles everything around them: watching for new episodes/dubs/subs, organizing files, refreshing your Plex or Jellyfin on completion, and sending notifications.  
Pick whichever downloader you want, or mix them per service (for example, ZLO7 for HiDive and multi-downloader-nx for Crunchyroll).

# Documentation
- Start here: [get-started.md](get-started.md). Pick your downloader, then follow the [multi-downloader-nx](mdnx-get-started.md) or [ZLO](zlo-get-started.md) guide to install, mount, and run the app.
- How-to guides: [guides/](guides/README.md). Set up a specific feature like notifications, media servers, or file organization.
- Full option reference: [config-options.md](config-options.md). Every configurable option, with defaults and JSON/YAML examples.

# Future plans
You can track progress of things [here](https://github.com/users/HyperNylium/projects/4)

# Acknowledgments
**This project would not be possible without the following third-party tools/packages:**

[Multi-downloader-nx](https://github.com/anidl/multi-downloader-nx)

ZLO7

[FFmpeg](https://ffmpeg.org/)

[MKVToolNix](https://mkvtoolnix.download/)

[Bento4-SDK](https://www.bento4.com/)

[Shaka Packager](https://github.com/stratumadev/shaka-packager)

# License
This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.
