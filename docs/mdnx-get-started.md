# Get started with multi-downloader-nx (Docker)

This guide sets up mdnx-auto-dl using **multi-downloader-nx** (aniDL) as the downloader for Crunchyroll, HiDive, and ADN.  
If you want to use ZLO instead, or mix the two, see [zlo-get-started.md](zlo-get-started.md).

### 1) Download `docker-compose.yaml` to your server
Save the [`docker-compose.yaml`](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/docker-compose.yaml) file:
```sh
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/docker-compose.yaml
```

### 2) Create required directories
```sh
mkdir -p ./appdata/logs
mkdir -p ./appdata/config
mkdir -p ./appdata/mdnx/config
mkdir -p ./appdata/mdnx/widevine
mkdir -p ./appdata/mdnx/playready
```

### 3) Add your CDM to the correct directory
You must provide your own CDM.

**Widevine CDM**
- Place a pair of `.bin` and `.pem` files **or** a single `.wvd` file into: `./appdata/mdnx/widevine`
- Uncomment the **Widevine bind-mount** in `docker-compose.yaml`
- More info: [GET-STARTED.md (Widevine)](https://github.com/anidl/multi-downloader-nx/blob/master/docs/GET-STARTED.md#widevine)

**Playready CDM**
- Place a pair of `bgroupcert.dat` and `zgpriv.dat` files **or** a single `.prd` into: `./appdata/mdnx/playready`
- Uncomment the **Playready bind-mount** in `docker-compose.yaml`
- More info: [GET-STARTED.md (Playready)](https://github.com/anidl/multi-downloader-nx/blob/master/docs/GET-STARTED.md#playready)

For legal reasons we do not include the CDM with the software, and you will have to source one yourself.  
Please do not open issues asking for these files. I can not give, nor instruct you on how to get these. Please Google around.

### 4) Provide the aniDL binary (multi-downloader-nx)
You must provide your own aniDL binary to enable any MDNX service (Crunchyroll, HiDive, or ADN through multi-downloader-nx).

- Download `multi-downloader-nx-linux-x64-cli.7z` from [multi-downloader-nx releases](https://github.com/anidl/multi-downloader-nx/releases/latest).
- Extract and place ONLY the `aniDL` binary at `./appdata/mdnx/aniDL` on your host.
- Uncomment the **multi-downloader-nx aniDL binary** bind-mount in `docker-compose.yaml`:
  ```yaml
  - ./appdata/mdnx/aniDL:/app/appdata/bin/mdnx/aniDL:rw
  ```
- Uncomment the **multi-downloader-nx config location** bind-mount in `docker-compose.yaml`:
  ```yaml
  - ./appdata/mdnx/config:/app/appdata/bin/mdnx/config:rw
  ```

If MDNX is enabled in your config but this binary is missing at startup, the container will exit with a critical log line telling you where the binary is expected.

### 5) Download a config file into `./appdata/config`
You can use either JSON or YAML. Pick one.

[`config.json`](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/appdata/config/config.json):
```sh
cd ./appdata/config
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/appdata/config/config.json
```

[`config.yaml`](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/appdata/config/config.yaml):
```sh
cd ./appdata/config
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/appdata/config/config.yaml
```

Both formats accept the same keys. The examples in this guide show both JSON and YAML, so follow whichever one you picked (see [config-options.md](config-options.md) for the full side-by-side reference).

### 6) Set where each provider saves its files
The config file has a top-level `destinations` section. Each provider you enable needs an entry that tells the app where to put finished files inside the container, and how to name the folders.

The shipped config already has one entry per provider, pointing at `/data/Anime` or `/data/TV Shows`. Both of those paths are mounted by the default `docker-compose.yaml`. If you only enable a few providers, you can delete the entries for the ones you do not use.

If you want to save files somewhere else on your host, change the **left** side of the bind-mount in `docker-compose.yaml` (for example, `./appdata/data/Anime` to `/mnt/chungus/Anime`) and keep the right side the same. If you want to change the right side (the path inside the container), update the matching `destinations.<service>.dir` in the config file too.

For the full list of variables you can use inside `folder_structure`, see [Options for `folder_structure`](config-options.md#options-for-folder_structure).

---

## Configure providers

<details>
  <summary>Crunchyroll (anidl/multi-downloader-nx)</summary>

  ### 1) Crunchyroll credentials
  Put your Crunchyroll username and password into these keys in your config file:

  JSON:
  ```json
  {
    "app": {
      "CR_ENABLED": true,
      "CR_USERNAME": "itsamemario@myemailprovider.com",
      "CR_PASSWORD": "thisismypassword123"
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CR_ENABLED: true
      CR_USERNAME: "itsamemario@myemailprovider.com"
      CR_PASSWORD: "thisismypassword123"
  ```

  Keep in mind that `CR_ENABLED` must be set to `true` for Crunchyroll's API to be used. By default it is set to `false`.

  ### 2) Crunchyroll series IDs to monitor
  Get the **series ID** from the Crunchyroll URL and add it under `cr_monitor_series_id`.

  Example URL:
  ```txt
  https://www.crunchyroll.com/series/GG5H5XQ7D/kaiju-no-8
  ```
  Series ID: `GG5H5XQ7D`

  Add it like this:

  JSON:
  ```json
  {
    "cr_monitor_series_id": {
      "GG5H5XQ7D": {}
    }
  }
  ```
  YAML:
  ```yaml
  cr_monitor_series_id:
      "GG5H5XQ7D": {}
  ```
</details>

<details>
  <summary>HiDive (anidl/multi-downloader-nx)</summary>

  ### 1) HiDive credentials
  Put your HiDive username and password into these keys in your config file:

  JSON:
  ```json
  {
    "app": {
      "HIDIVE_ENABLED": true,
      "HIDIVE_USERNAME": "itsamemario@myemailprovider.com",
      "HIDIVE_PASSWORD": "thisismypassword123"
    }
  }
  ```
  YAML:
  ```yaml
  app:
      HIDIVE_ENABLED: true
      HIDIVE_USERNAME: "itsamemario@myemailprovider.com"
      HIDIVE_PASSWORD: "thisismypassword123"
  ```

  Keep in mind that `HIDIVE_ENABLED` must be set to `true` for HiDive's API to be used. By default it is set to `false`.

  ### 2) HiDive series IDs to monitor
  Get the **series ID** from HiDive and add it under `hidive_monitor_series_id`.

  Steps:
  1. Go to [HiDive's search site](https://www.hidive.com/search). No login required.
  2. Click on the "Filter" button and select "Series" under "Content".
  3. Search for what you want to monitor (example: "Call of the night").
  4. Click the search result to open the series page. The URL will look like:
     ```txt
     https://www.hidive.com/season/19079?seriesId=1050
     ```
     Series ID: `1050`

  Add it like this:

  JSON:
  ```json
  {
    "hidive_monitor_series_id": {
      "1050": {}
    }
  }
  ```
  YAML:
  ```yaml
  hidive_monitor_series_id:
      "1050": {}
  ```
</details>

<details>
  <summary>ADN (anidl/multi-downloader-nx)</summary>

  ### 1) ADN credentials
  Put your ADN (Animation Digital Network) username and password into these keys in your config file:

  JSON:
  ```json
  {
    "app": {
      "ADN_ENABLED": true,
      "ADN_USERNAME": "itsamemario@myemailprovider.com",
      "ADN_PASSWORD": "thisismypassword123"
    }
  }
  ```
  YAML:
  ```yaml
  app:
      ADN_ENABLED: true
      ADN_USERNAME: "itsamemario@myemailprovider.com"
      ADN_PASSWORD: "thisismypassword123"
  ```

  Keep in mind that `ADN_ENABLED` must be set to `true` for ADN's API to be used. By default it is set to `false`.

  ### 2) ADN series IDs to monitor
  Get the **series ID** from the ADN URL (the numeric ID in the series path) and add it under `adn_monitor_series_id`.

  Example URL:
  ```txt
  https://animationdigitalnetwork.com/video/442-sword-art-online
  ```
  Series ID: `442`

  Add it like this:

  JSON:
  ```json
  {
    "adn_monitor_series_id": {
      "442": {}
    }
  }
  ```
  YAML:
  ```yaml
  adn_monitor_series_id:
      "442": {}
  ```
</details>

---

## Start the container

```sh
docker compose up -d
```

That's it! The application will now keep track of the series you listed in your config file, automatically download new episodes as they're released, and update existing downloads whenever new dubs or subs become available.

---

## Next steps

Set up notifications, media-server refreshes, file organization, and more in the [how-to guides](guides/README.md). For the full picture, see [Next steps](get-started.md#next-steps) and the [Remote-specials override](get-started.md#remote-specials-override) in the main guide.
