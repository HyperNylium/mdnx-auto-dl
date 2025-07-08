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

And paste in the following. These are defaults. Feel free to change what you like.
All settings under "mdnx" refer to that services settings.
For example, the key-vaule pairs under "bin-path" will modify multi-download-nx's `bin-path.yml` file.
In `app`, things are a little different. Anything that is by itself, for example, `TEMP_DIR` are global env vars. Anything that has a module name before it, for example, `MDNX_API_FORCE_REAUTH`, will modify the `FORCE_REAUTH` option for the `MDNX_API.py` module.
These will later become variables you can put into the `docker-compose.yaml` environment section.
```json
{
    "monitor-series-id": [],
    "app": {
        "TEMP_DIR": "/app/appdata/temp",
        "BIN_DIR": "/app/appdata/bin",
        "LOG_FILE": "/app/appdata/logs/app.log",
        "DATA_DIR": "/data",
        "MDNX_API_FORCE_REAUTH": false,
        "MDNX_API_SKIP_TEST": false,
        "MDNX_SERVICE_USERNAME": "",
        "MDNX_SERVICE_PASSWORD": "",
        "MAIN_LOOP_UPDATE_INTERVAL": 3600,
        "MAIN_LOOP_BETWEEN_EPISODE_WAIT_INTERVAL": 20
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
            "fileName": "${seriesTitle} - S${season}E${episode}",
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
        },
        "gui": {
            "port": 3000
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

# Some notes

1. The expected folder structure is
```
/data/[anime name]/[short season number, like S1]/[anime name] - [long season number][long episode number]
```
Example:
```
/data/Frieren Beyond Journey's End/S1/Frieren Beyond Journey's End - S01E01
```

So go into your left-side mountpoint to `/data` and check the folder structure.
If it is different, please make a seperate library and a blank folder.

As reference, here is my folder structure:
```
Mountpoint: /mnt/plexdata/Anime:/data:rw
Contents of "/mnt/plexdata/Anime":
├───365 Days To The Wedding
│   └───S1
│           365 Days To The Wedding - S01E01.mkv
│           365 Days To The Wedding - S01E02.mkv
│           365 Days To The Wedding - S01E03.mkv
│           365 Days To The Wedding - S01E04.mkv
│           365 Days To The Wedding - S01E05.mkv
│           365 Days To The Wedding - S01E06.mkv
│           365 Days To The Wedding - S01E07.mkv
│           365 Days To The Wedding - S01E08.mkv
│           365 Days To The Wedding - S01E09.mkv
│           365 Days To The Wedding - S01E10.mkv
│           365 Days To The Wedding - S01E11.mkv
│           365 Days To The Wedding - S01E12.mkv
│
├───4 CUT HERO
│   └───S1
│           4 CUT HERO - S01E01.mkv
│           4 CUT HERO - S01E02.mkv
│           4 CUT HERO - S01E03.mkv
│           4 CUT HERO - S01E04.mkv
│           4 CUT HERO - S01E05.mkv
│           4 CUT HERO - S01E06.mkv
│           4 CUT HERO - S01E07.mkv
│           4 CUT HERO - S01E08.mkv
│           4 CUT HERO - S01E09.mkv
│           4 CUT HERO - S01E10.mkv
│
├───7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy
│   └───S1
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E01.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E02.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E03.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E04.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E05.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E06.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E07.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E08.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E09.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E10.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E11.mkv
│           7th Time Loop - The Villainess Enjoys a Carefree Life Married to Her Worst Enemy - S01E12.mkv
│
├───86 EIGHTY-SIX
│   ├───S1
│   │       86 EIGHTY-SIX - S01E01.mkv
│   │       86 EIGHTY-SIX - S01E02.mkv
│   │       86 EIGHTY-SIX - S01E03.mkv
│   │       86 EIGHTY-SIX - S01E04.mkv
│   │       86 EIGHTY-SIX - S01E05.mkv
│   │       86 EIGHTY-SIX - S01E06.mkv
│   │       86 EIGHTY-SIX - S01E07.mkv
│   │       86 EIGHTY-SIX - S01E08.mkv
│   │       86 EIGHTY-SIX - S01E09.mkv
│   │       86 EIGHTY-SIX - S01E10.mkv
│   │       86 EIGHTY-SIX - S01E11.mkv
│   │       86 EIGHTY-SIX - S01E12.mkv
│   │       86 EIGHTY-SIX - S01E13.mkv
│   │       86 EIGHTY-SIX - S01E14.mkv
│   │       86 EIGHTY-SIX - S01E15.mkv
│   │       86 EIGHTY-SIX - S01E16.mkv
│   │       86 EIGHTY-SIX - S01E17.mkv
│   │       86 EIGHTY-SIX - S01E18.mkv
│   │       86 EIGHTY-SIX - S01E19.mkv
│   │       86 EIGHTY-SIX - S01E20.mkv
│   │       86 EIGHTY-SIX - S01E21.mkv
│   │       86 EIGHTY-SIX - S01E22.mkv
│   │       86 EIGHTY-SIX - S01E23.mkv
│   │
│   └───Special
│           86 EIGHTY-SIX - S00E01.mkv
│           86 EIGHTY-SIX - S00E03.mkv
│           86 EIGHTY-SIX - S00E04.mkv
│
├───91 Days
│   ├───S1
│   │       91 Days - S01E01.mkv
│   │       91 Days - S01E02.mkv
│   │       91 Days - S01E03.mkv
│   │       91 Days - S01E04.mkv
│   │       91 Days - S01E05.mkv
│   │       91 Days - S01E06.mkv
│   │       91 Days - S01E07.mkv
│   │       91 Days - S01E08.mkv
│   │       91 Days - S01E09.mkv
│   │       91 Days - S01E10.mkv
│   │       91 Days - S01E11.mkv
│   │       91 Days - S01E12.mkv
│   │
│   └───Special
│           91 Days - S00E01.mkv
│
├───A Certain Scientific Accelerator
│   ├───S1
│   │       A Certain Scientific Accelerator - S01E01.mkv
│   │       A Certain Scientific Accelerator - S01E02.mkv
│   │       A Certain Scientific Accelerator - S01E03.mkv
│   │       A Certain Scientific Accelerator - S01E04.mkv
│   │       A Certain Scientific Accelerator - S01E05.mkv
│   │       A Certain Scientific Accelerator - S01E06.mkv
│   │       A Certain Scientific Accelerator - S01E07.mkv
│   │       A Certain Scientific Accelerator - S01E08.mkv
│   │       A Certain Scientific Accelerator - S01E09.mkv
│   │       A Certain Scientific Accelerator - S01E10.mkv
│   │       A Certain Scientific Accelerator - S01E11.mkv
│   │       A Certain Scientific Accelerator - S01E12.mkv
│   │
│   └───Specials
│           A Certain Scientific Accelerator - S00E01.mkv
...
```

2. I plan to add the following features after i make sure this works on its own:
- Somehow transcode the .mkv files from what they are to HEVC, or something else. Currently, every episode is ~1.2 - 1.5GB.
- Add audio options using [mkv-auto](https://github.com/philiptn/mkv-auto) if you want to have [whatever CR auido is] -> EOS for example. Higher vocals, lower booms.
- Add capability to set different `/data` folder structures.
- Add capability to rename seasons correctly. Sometimes, CR has season 66 or whatever for season 4. Wrong season number is also passed through multi-download-nx - which is expected and is totally fine. Maybe include seasons first and last episode in TVDB search and figure out what season it came from using said episode names. This would also help for things like S02E13. Season 2 episode 1 turned into episode 13.
