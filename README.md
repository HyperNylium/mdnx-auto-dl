# MDNX-auto-dl

## Legal Warning
This application is not endorsed by or affiliated with Crunchyroll, Hidive, AnimeOnegai, or AnimationDigitalNetwork. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the Terms of Service between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

# What is this?
MDNX-auto-dl is a free and open-source Python application that monitors and downloads anime from Crunchyroll. Its main usage is to monitor new anime that has weekly episodes and download them to your plex/jellyfin/emby server.
This application only supports downloads from Crunchyroll at the moment even though multi-download-nx supports more services. This may change in the future, but not planned as i dont have an account with other services.

# Get started
1. Save the `docker-compose.yaml` file to your server.
```
services:
  mdnx-auto-dl:
    ### Build image locally if you want.
    ### Requires all files from repo to be present.
    ### run "git clone https://github.com/HyperNylium/mdnx-auto-dl.git && cd mdnx-auto-dl" to get started
    # build:
    #   context: .
    #   dockerfile: Dockerfile

    ### Use local image if you manually ran "docker build -t mdnx-auto-dl:latest ."
    # image: mdnx-auto-dl:latest

    ### Use public image (recommended).
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
      # I suggest to make a separate "active-anime" library and mount that here.
      # Only modify the left side ("./appdata/data") not the right.
      # Example:
      #- /mnt/plexdata/active-anime:/data:rw
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
In `app`, things are a little different. Anything that is by itself, for example, `TEMP_DIR` are global variables (all modules can use said variable).\
Anything that has a module name before it, for example, `MDNX_API_FORCE_REAUTH`, will modify the `FORCE_REAUTH` option for the `MDNX_API.py` module. \
These are planned to later become variables you can put into the `docker-compose.yaml` environment section. But thats in the future, not right now :)
```json
{
    "monitor-series-id": [],
    "app": {
        "TEMP_DIR": "/app/appdata/temp",
        "BIN_DIR": "/app/appdata/bin",
        "LOG_FILE": "/app/appdata/logs/app.log",
        "DATA_DIR": "/data",
        "FOLDER_STRUCTURE": "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}",
        "MDNX_API_FORCE_REAUTH": false,
        "MDNX_API_SKIP_TEST": false,
        "MDNX_SERVICE_USERNAME": "",
        "MDNX_SERVICE_PASSWORD": "",
        "MAIN_LOOP_UPDATE_INTERVAL": 3600,
        "MAIN_LOOP_BETWEEN_EPISODE_WAIT_INTERVAL": 20,
        "MAIN_LOOP_DOWNLOAD_SPECIAL_EPISODES": true
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
                "eng",
                "jpn"
            ],
            "dlsubs": [
                "en"
            ],
            "defaultAudio": "jpn",
            "timeout": 30000,
            "waittime": 3000,
            "mp4": false,
            "nocleanup": false,
            "dlVideoOnce": false,
            "keepAllVideos": false
        },
        "dir-path": {
            "content": "/app/appdata/temp",
            "fonts": "./fonts/"
        }
    }
}
```

5. Put in your Crunchyroll username and password into the following key-value pairs in `config.json`
```
MDNX_SERVICE_USERNAME
MDNX_SERVICE_PASSWORD
```

4. Start the container
```
docker compose up -d
```

That should be it!

# Future plans
I plan to add the following features after i make sure this works on its own:
- Somehow transcode the .mkv files from what they are to HEVC, or something else. Currently, every episode is ~1.2 - 1.5GB.
- Add audio options using [mkv-auto](https://github.com/philiptn/mkv-auto) if you want to have [whatever CR auido is] -> EOS for example. Higher vocals, lower booms.
- Add capability to set different `/data` folder structures. (done as of v0.0.4. Need to test and write docs)
- Add capability to monitor dubs. Currently, it only monitors if new episodes are available and downloads them according to what you have set in `config["app"]["mdnx"]["cli-defaults"]`. In the future, i would like to add a way to monitor if a `jpn` only episode now has an `eng` dub available and download it, overwriting the episode already in `DATA_DIR`. the `jpn` and `eng` would be from `dubLang` in `config.json`, not hardcoded. (done as of v0.0.5. Need to test and write docs. Also monitors subs)
- Add capability to rename seasons correctly. Sometimes, CR has season 66 or whatever for season 4. Wrong season number is also passed through multi-download-nx - which is expected. Maybe include seasons first and last episode in TVDB search and figure out what season it came from using said episode names.
- I was not able to figure out a great way to download the [Bento4-SDK](https://www.bento4.com/downloads/) and [multi-download-nx](https://github.com/anidl/multi-downloader-nx/releases/latest) packages. \
    For now, both are download from my webserver. There are the URLs:
    - https://cdn.hypernylium.com/mdnx-auto-dl/Bento4-SDK.zip
    - https://cdn.hypernylium.com/mdnx-auto-dl/mdnx.zip \
Every dependency is included in the image (ffmpeg and mkvmerge) and downloaded/installed from debian repositories (apt install). \
If you find a better way to do this (and it actually works), please open a PR. I would happily accept it! \
Preferably, the Bento4-SDK and multi-download-nx packages should be downloaded from their respective websites and using the `entrypoint.sh` script to install them.

# Acknowledgments
**This project would not be possible without the following third-party tools/packages:**

[Multi-download-nx](https://github.com/anidl/multi-downloader-nx)

[FFmpeg](https://ffmpeg.org/)

[MKVToolNix](https://mkvtoolnix.download/)

[Bento4-SDK](https://www.bento4.com/)

# License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
