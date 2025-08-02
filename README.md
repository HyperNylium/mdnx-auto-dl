# MDNX-auto-dl

## Legal Warning
This application is not endorsed by or affiliated with Crunchyroll, Hidive, AnimeOnegai, or AnimationDigitalNetwork. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the Terms of Service between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

# What is this?
MDNX-auto-dl is a free and open-source Python application that monitors and downloads anime from Crunchyroll. Its main usage is to monitor new anime that has weekly episodes and download them to your plex/jellyfin/emby server.
This application only supports downloads from Crunchyroll at the moment even though multi-download-nx supports more services. This may change in the future, but not planned as i dont have an account with other services.

# Get started
1. Save the `docker-compose.yaml` file to your server.
```yaml
services:
  mdnx-auto-dl:
    image: ghcr.io/hypernylium/mdnx-auto-dl:latest
    container_name: mdnx-auto-dl
    restart: unless-stopped
    volumes:
      # log file location
      - ./appdata/logs:/app/appdata/logs:rw

      # mdnx-auto-dl config location.
      # This will house config.json and queue.json.
      - ./appdata/config:/app/appdata/config:rw

      # multi-download-nx config and widevine folder locations
      # to keep cr_token.yml and make DRM decryption possible
      - ./appdata/mdnx/widevine:/app/appdata/bin/mdnx/widevine:rw
      - ./appdata/mdnx/config:/app/appdata/bin/mdnx/config:rw

      # plex/jellyfin/emby anime storage location.
      # Only modify the left side ("./appdata/data"), not the right.
      # Example:
      #- /mnt/plexdata/Anime:/data:rw
      - ./appdata/data:/data:rw
    environment:
      - UID=1000
      - GID=1000
      - TZ=America/New_York
```

2. Make required dirs
```
mkdir -p ./appdata/logs
mkdir -p ./appdata/config
mkdir -p ./appdata/mdnx/widevine
mkdir -p ./appdata/mdnx/config

# Optional if not using SMB or NFS share. 
# Make sure to update compose file with desired file storage
mkdir -p ./appdata/data
```

3. Put in your widevine `device_client_id_blob.bin` and `device_private_key.pem` files. For legal reasons we do not include the CDM with the software, and you will have to source one yourself. Please do not open issues asking for these files. I can not give, nor instruct you on how to get these. Please Google around.

3. Save `config.json` to `./appdata/config`
```
cd ./appdata/config
nano config.json
```

And paste in the following. These are defaults. Feel free to change what you like. \
All settings under "mdnx" refer to that services settings. \
For example, the key-vaule pairs under "bin-path" will modify multi-download-nx's `bin-path.yml` file. \
These are planned to later become variables you can put into the `docker-compose.yaml` environment section. But thats in the future, not right now :)
```json
{
    "monitor-series-id": [],
    "app": {
        "TEMP_DIR": "/app/appdata/temp",
        "BIN_DIR": "/app/appdata/bin",
        "LOG_FILE": "/app/appdata/logs/app.log",
        "DATA_DIR": "/data",
        "CR_USERNAME": "",
        "CR_PASSWORD": "",
        "BACKUP_DUBS": ["zho"],
        "FOLDER_STRUCTURE": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}",
        "DOWNLOAD_SPECIAL_EPISODES": false,
        "SPECIAL_EPISODES_FOLDER_NAME": "Special",
        "CHECK_MISSING_DUB_SUB": true,
        "CHECK_MISSING_DUB_SUB_TIMEOUT": 300,
        "CHECK_FOR_UPDATES_INTERVAL": 3600,
        "BETWEEN_EPISODE_DL_WAIT_INTERVAL": 30,
        "CR_FORCE_REAUTH": false,
        "CR_SKIP_API_TEST": false,
        "NOTIFICATION_PREFERENCE": "none",
        "REMOVE_ALL_ACTIVE_STREAMS": false,
        "LOG_LEVEL": "info"
    },
    "mdnx": {
        "bin-path": {
            "ffmpeg": "ffmpeg",
            "ffprobe": "ffprobe",
            "mkvmerge": "mkvmerge",
            "mp4decrypt": "/app/appdata/bin/Bento4-SDK/bin/mp4decrypt"
        },
        "cli-defaults": {
            "q": 0,
            "kstream": 1,
            "server": 1,
            "partsize": 3,
            "fileName": "output",
            "dubLang": [
                "jpn",
                "eng"
            ],
            "dlsubs": [
                "en"
            ],
            "defaultAudio": "jpn",
            "defaultSub": "eng",
            "timeout": 30000,
            "waittime": 3000,
            "mp4": false,
            "nocleanup": false,
            "dlVideoOnce": false,
            "keepAllVideos": false,
            "skipUpdate": true,
            "vstream": "samsungtv",
            "astream": "android"
        },
        "dir-path": {
            "content": "/app/appdata/temp",
            "fonts": "./fonts/"
        }
    }
}
```

5. Put in your Crunchyroll username and password into the following key-value pairs in `config.json`. You will be putting then in the `""` quotes.
```
CR_USERNAME
CR_PASSWORD
```
Example:
```json
{
    "app": {
        "CR_USERNAME": "itsamemario@myemailprovider.com",
        "CR_PASSWORD": "thisismypassword123",
        ...
    }
}
```

6. Get the series ID of the anime you want to monitor and put them into the `monitor-series-id` list in `config.json`. \
Lets sat you want to monitor Kaiju No. 8. You would go to the anime's page on Crunchyroll and copy the series ID from the URL. \
Example:
```
https://www.crunchyroll.com/series/GG5H5XQ7D/kaiju-no-8
```
The series ID is `GG5H5XQ7D`.

You would then put it into the `monitor-series-id` list in `config.json` like so:
```json
{
    "monitor-series-id": [
        "GG5H5XQ7D"
    ],
    ...
}
```

7. Start the container
```
docker compose up -d
```

And you are done! The application will now monitor the series you have specified in `config.json` and download new episodes as they become available!

# Docs
This is not the entire documentation that i want, but it will do for now. In the future, i will have a more detailed seperate documentation file with examples. \
If you have any questions, please open an issue and i will try to help you :)

| Config                             | Default value                                                                 | Explanation                                                                                                    |
| :--------------------------------- | :---------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------------------------- |
| `monitor-series-id`                | `[]`                                                                          | List of Crunchyroll series IDs to watch for new episodes.                                                      |
| `TEMP_DIR`                         | `/app/appdata/temp`                                                           | Temporary staging directory. Raw downloads are written here before moving into your library.                   |
| `BIN_DIR`                          | `/app/appdata/bin`                                                            | Path containing bundled binaries (e.g. `multi-download-nx`, `Bento4-SDK`) inside the container.                |
| `LOG_FILE`                         | `/app/appdata/logs/app.log`                                                   | Absolute path of the application log file in the container.                                                    |
| `DATA_DIR`                         | `/data`                                                                       | Root of your anime library on the host. Finished files are organized here according to `FOLDER_STRUCTURE`.     |
| `CR_USERNAME`                      | `""`                                                                          | Crunchyroll username for authentication.                                                                       |
| `CR_PASSWORD`                      | `""`                                                                          | Crunchyroll password for authentication.                                                                       |
| `BACKUP_DUBS`                      | `["zho"]`                                                                     | List of backup dubs to download if the primary dubs are not available.                                         |
| `FOLDER_STRUCTURE`                 | `${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}`| Template for how seasons and episodes are laid out under `DATA_DIR`.                                           |
| `DOWNLOAD_SPECIAL_EPISODES`        | `false`                                                                       | If `true`, download special episodes (e.g. `S00EXX`, movies); if `false`, ignore them.                         |
| `SPECIAL_EPISODES_FOLDER_NAME`     | `Special`                                                                     | Folder name (inside each series) that stores special episodes.                                                 |
| `CHECK_MISSING_DUB_SUB`            | `true`                                                                        | When `true`, detect and report episodes missing dub or subtitle tracks.                                        |
| `CHECK_MISSING_DUB_SUB_TIMEOUT`    | `300`                                                                         | Seconds to wait before timing out when checking for missing dubs/subs on a file.                               |
| `CHECK_FOR_UPDATES_INTERVAL`       | `3600`                                                                        | Seconds to wait between complete library scans for new episodes or missing tracks.                             |
| `BETWEEN_EPISODE_DL_WAIT_INTERVAL` | `30`                                                                          | Delay in seconds after each episode download to reduce API rate‑limiting.                                      |
| `CR_FORCE_REAUTH`                  | `false`                                                                       | When `true`, always perform a fresh Crunchyroll login and overwrite `cr_token.yml`, then reset to `false`.     |
| `CR_SKIP_API_TEST`                 | `false`                                                                       | When `true`, skip the startup self‑test that probes the Crunchyroll API.                                       |
| `NOTIFICATION_PREFERENCE`          | `none`                                                                        | Set what service you want to use to receive notifications. Options: `none`, `smtp`,`ntfy`.                     |
| `LOG_LEVEL`                        | `info`                                                                        | Set the logging level. Options: `debug`, `info`, `warning`, `error`, `critical`.                               |
| `REMOVE_ALL_ACTIVE_STREAMS`        | `false`                                                                       | When `true`, remove all active streams before starting a new download. Sets `--tsd` to `true` in mdnx          |


Options for `FOLDER_STRUCTURE`  
| Variable           | Example value                | Explanation |
| :----------------- | :--------------------------: | :---------- |
| `${seriesTitle}`   | `Kaiju No. 8`                | Sanitised series title (filesystem-unsafe characters replaced). |
| `${season}`        | `1`                          | Season number, no leading zeros. |
| `${seasonPadded}`  | `01`                         | Season number padded to two digits. |
| `${episode}`       | `1`                          | Episode number, no leading zeros. |
| `${episodePadded}` | `01`                         | Episode number padded to two digits. |
| `${episodeName}`   | `The Man Who Became a Kaiju` | Sanitised episode title. |

Example of `FOLDER_STRUCTURE` with the above variables:
```
${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}
```
This would result in the following folder structure:
```
Kaiju No. 8/S1/Kaiju No. 8 - S01E01
```

Options for `NOTIFICATION_PREFERENCE`
| Option | Explanation |
| :----- | :---------- |
| `none` | No notifications will be sent. |
| `smtp` | Send notifications via SMTP email. Requires additional configuration in `config.json`.
| `ntfy` | Send notifications via ntfy.sh. Requires additional configuration in `config.json` and `app/appdata/config/ntfy.sh` |

For `smtp`, add the following key-value pairs to `config.json` right under the `NOTIFICATION_PREFERENCE` key:
```json
"NOTIFICATION_PREFERENCE": "smtp",
"SMTP_FROM": "who we sending as?",
"SMTP_TO": "who we sending to?",
"SMTP_HOST": "smtp.gmail.com, or whatever your email provider is",
"SMTP_USERNAME": "your username. For gmail, this is your email address",
"SMTP_PASSWORD": "your password. For gmail, this is your app password",
"SMTP_PORT": 587,
"SMTP_STARTTLS": true
```

For `ntfy`, add the following key-value pairs to `config.json` right under the `NOTIFICATION_PREFERENCE` key:
```json
"NOTIFICATION_PREFERENCE": "ntfy",
"NTFY_SCRIPT_PATH": "/app/appdata/config/ntfy.sh"
```
Make sure to set `NTFY_URL` in `app/appdata/config/ntfy.sh` to the URL of your ntfy server. \
To modify things like tags and such, you can modify the `ntfy.sh` script.


# Future plans
I plan to add the following features after i get the basics working:
- [ ] Somehow transcode the .mkv files from what they are to HEVC, or something else. Currently, every episode is ~1.2 - 1.5GB with movies being +6GB.

- [ ] Add audio options using [mkv-auto](https://github.com/philiptn/mkv-auto) if you want to have [whatever CR auido is] -> EOS for example. Higher vocals, lower booms.

- [x] Add capability to set different `/data` folder structures. (done as of v0.0.4)

- [x] Add capability to monitor dubs. Currently, it only monitors if new episodes are available and downloads them according to what you have set in `config["app"]["mdnx"]["cli-defaults"]`. In the future, i would like to add a way to monitor if a `jpn` only episode now has an `eng` dub available and download it, overwriting the episode already in `DATA_DIR`. the `jpn` and `eng` would be from `dubLang` in `config.json`, not hardcoded. (done as of v0.0.5. Also monitors subs using whats set in `dlsubs`)

- [x] Add capability to rename seasons correctly. Sometimes, CR has season 66 or whatever for season 4. Wrong season number is also passed through multi-download-nx - which is expected. (done as of v0.0.5)

- [ ] When downloading the episode is finished and `file_handler.transfer()` is called. Instead of just naming the file S01E01 or whatever i was able to guess from multi-download-nx's output, i would like to somehow get episode details from TheTVDB. The importence of this is not really the individual episode names, but more the episode codes. If we download a special episode, which then gets moved to `Specials/S00E01`, how do we know its actually `S00E01` and not `S00E03`? Plex may show the wrong metadata or not show the episode at all. Thats what i aim to solve with TheTVDB API searches. This would only really benefit special episodes and anime that has weird season naming. An example of that is the duke of death and his maid. Some DBs say it has 1 season, but CR says it has 3 season, each season having 12 episodes. Hopfully i can cook something up in the future to help with this episode naming stuff haha.

- [x] Add dependencies in the container itself, no downloading from my webserver.

- [x] Add notification support for at least SMTP. (done as of 0.0.9)

# Acknowledgments
**This project would not be possible without the following third-party tools/packages:**

[Multi-download-nx](https://github.com/anidl/multi-downloader-nx)

[FFmpeg](https://ffmpeg.org/)

[MKVToolNix](https://mkvtoolnix.download/)

[Bento4-SDK](https://www.bento4.com/)

# License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
