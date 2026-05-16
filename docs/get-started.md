## Get started (Docker)

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
mkdir -p ./appdata/zlo/config
```

### 3) Add your CDM to the correct directory
You must provide your own CDM. This is only required for multi-downloader-nx.

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

### 4) Download a config file into `./appdata/config`
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

Both formats accept the same keys. The rest of this guide shows examples in JSON, but YAML works the same way (see [config-options.md](config-options.md) for side-by-side examples).

### 5) Set where each provider saves its files
The config file has a top-level `destinations` section. Each provider you enable needs an entry that tells the app where to put finished files inside the container, and how to name the folders.

The shipped config already has one entry per provider, pointing at `/data/Anime` or `/data/TV Shows`. Both of those paths are mounted by the default `docker-compose.yaml`. If you only enable a few providers, you can delete the entries for the ones you do not use.

If you want to save files somewhere else on your host, change the **left** side of the bind-mount in `docker-compose.yaml` (for example, `./appdata/data/Anime` to `/mnt/chungus/Anime`) and keep the right side the same. If you want to change the right side (the path inside the container), update the matching `destinations.<service>.dir` in the config file too.

For the full list of variables you can use inside `folder_structure`, see [Options for `folder_structure`](config-options.md#options-for-folder_structure).

---

## Configure providers

<details>
  <summary>Crunchyroll (anidl/multi-downloader-nx)</summary>

  ### 1) Crunchyroll credentials
  Put your Crunchyroll username and password into these keys in `config.json` (inside the `""` quotes):
  ```json
  {
    "app": {
      "CR_ENABLED": true,
      "CR_USERNAME": "itsamemario@myemailprovider.com",
      "CR_PASSWORD": "thisismypassword123"
    }
  }
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
  ```json
  {
    "cr_monitor_series_id": {
      "GG5H5XQ7D": {}
    }
  }
  ```
</details>

<details>
  <summary>HiDive (anidl/multi-downloader-nx)</summary>

  ### 1) HiDive credentials
  Put your HiDive username and password into these keys in `config.json` (inside the `""` quotes):
  ```json
  {
    "app": {
      "HIDIVE_ENABLED": true,
      "HIDIVE_USERNAME": "itsamemario@myemailprovider.com",
      "HIDIVE_PASSWORD": "thisismypassword123"
    }
  }
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
  ```json
  {
    "hidive_monitor_series_id": {
      "1050": {}
    }
  }
  ```
</details>

<details>
  <summary>ADN (anidl/multi-downloader-nx)</summary>

  ### 1) ADN credentials
  Put your ADN (Animation Digital Network) username and password into these keys in `config.json` (inside the `""` quotes):
  ```json
  {
    "app": {
      "ADN_ENABLED": true,
      "ADN_USERNAME": "itsamemario@myemailprovider.com",
      "ADN_PASSWORD": "thisismypassword123"
    }
  }
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
  ```json
  {
    "adn_monitor_series_id": {
      "442": {}
    }
  }
  ```
</details>

> [!NOTE]
> The ZLO sections below all share the same prerequisite. ZLO is a separate downloader from multi-downloader-nx. It uses its own binary (`zlo7`) and its own settings folder. You must already have a working `zlo7` binary and a logged-in settings folder before turning it on here. mdnx-auto-dl only runs the binary. It does not log you in, nor check if your credentials are correct.

<details>
  <summary>Crunchyroll (ZLO)</summary>

  ### 1) Mount the ZLO binary and settings folder
  Place your `zlo7` binary at `./appdata/zlo/zlo7` (`zlo7` being the binary name) and your already-logged-in zlo7 `settings` folder content at `./appdata/zlo/config`.  
  The folder can be found at `C:\Users\<your username>\Documents\zlo7\settings` on Windows, or `~/Documents/zlo7/settings` on Linux.

  Then uncomment the **ZLO config** bind-mounts in `docker-compose.yaml`:
  ```yaml
  - ./appdata/zlo/zlo7:/app/appdata/bin/zlo/zlo7:rw
  - ./appdata/zlo/config:/home/mdnx-auto-dl/Documents/zlo7:rw
  ```

  ### 2) Enable Crunchyroll (ZLO)
  Set [`ZLO_CR_ENABLED`](config-options.md#ZLO_CR_ENABLED) to `true` in `config.json`:
  ```json
  {
    "app": {
      "ZLO_CR_ENABLED": true
    }
  }
  ```

  ### 3) Crunchyroll series IDs to monitor
  Get the **series ID** from the Crunchyroll URL and add it under `zlo_cr_monitor_series_id`.

  Example URL:
  ```txt
  https://www.crunchyroll.com/series/GG5H5XQ7D/kaiju-no-8
  ```
  Series ID: `GG5H5XQ7D`

  Add it like this:
  ```json
  {
    "zlo_cr_monitor_series_id": {
      "GG5H5XQ7D": {}
    }
  }
  ```

  ### 4) Optional: tune ZLO Crunchyroll download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>HiDive (ZLO)</summary>

  ### 1) Mount the ZLO binary and settings folder
  Place your `zlo7` binary at `./appdata/zlo/zlo7` (`zlo7` being the binary name) and your already-logged-in zlo7 `settings` folder content at `./appdata/zlo/config`.  
  The folder can be found at `C:\Users\<your username>\Documents\zlo7\settings` on Windows, or `~/Documents/zlo7/settings` on Linux.

  Then uncomment the **ZLO config** bind-mounts in `docker-compose.yaml`:
  ```yaml
  - ./appdata/zlo/zlo7:/app/appdata/bin/zlo/zlo7:rw
  - ./appdata/zlo/config:/home/mdnx-auto-dl/Documents/zlo7:rw
  ```

  ### 2) Enable HiDive (ZLO)
  Set [`ZLO_HIDIVE_ENABLED`](config-options.md#ZLO_HIDIVE_ENABLED) to `true` in `config.json`:
  ```json
  {
    "app": {
      "ZLO_HIDIVE_ENABLED": true
    }
  }
  ```

  ### 3) HiDive series IDs to monitor
  Get the **series ID** from HiDive and add it under `zlo_hidive_monitor_series_id`.

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
  ```json
  {
    "zlo_hidive_monitor_series_id": {
      "1050": {}
    }
  }
  ```

  ### 4) Optional: tune ZLO HiDive download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>ADN (ZLO)</summary>

  ### 1) Mount the ZLO binary and settings folder
  Place your `zlo7` binary at `./appdata/zlo/zlo7` (`zlo7` being the binary name) and your already-logged-in zlo7 `settings` folder content at `./appdata/zlo/config`.  
  The folder can be found at `C:\Users\<your username>\Documents\zlo7\settings` on Windows, or `~/Documents/zlo7/settings` on Linux.

  Then uncomment the **ZLO config** bind-mounts in `docker-compose.yaml`:
  ```yaml
  - ./appdata/zlo/zlo7:/app/appdata/bin/zlo/zlo7:rw
  - ./appdata/zlo/config:/home/mdnx-auto-dl/Documents/zlo7:rw
  ```

  ### 2) Enable ADN (ZLO)
  Set [`ZLO_ADN_ENABLED`](config-options.md#ZLO_ADN_ENABLED) to `true` in `config.json`:
  ```json
  {
    "app": {
      "ZLO_ADN_ENABLED": true
    }
  }
  ```

  ### 3) ADN series IDs to monitor
  Get the **series ID** from the ADN URL and add it under `zlo_adn_monitor_series_id`.

  Add it like this:
  ```json
  {
    "zlo_adn_monitor_series_id": {
      "your-adn-series-id": {}
    }
  }
  ```

  ### 4) Optional: tune ZLO ADN download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>Disney+ (ZLO)</summary>

  ### 1) Mount the ZLO binary and settings folder
  Place your `zlo7` binary at `./appdata/zlo/zlo7` (`zlo7` being the binary name) and your already-logged-in zlo7 `settings` folder content at `./appdata/zlo/config`.  
  The folder can be found at `C:\Users\<your username>\Documents\zlo7\settings` on Windows, or `~/Documents/zlo7/settings` on Linux.

  Then uncomment the **ZLO config** bind-mounts in `docker-compose.yaml`:
  ```yaml
  - ./appdata/zlo/zlo7:/app/appdata/bin/zlo/zlo7:rw
  - ./appdata/zlo/config:/home/mdnx-auto-dl/Documents/zlo7:rw
  ```

  ### 2) Enable Disney+ (ZLO)
  Set [`ZLO_DISNEYPLUS_ENABLED`](config-options.md#ZLO_DISNEYPLUS_ENABLED) to `true` in `config.json`:
  ```json
  {
    "app": {
      "ZLO_DISNEYPLUS_ENABLED": true
    }
  }
  ```

  ### 3) Disney+ series IDs to monitor
  Get the **series ID** from the Disney+ URL and add it under `zlo_disneyplus_monitor_series_id`.

  Steps:
  1. Go to [Disney's search site](https://www.disneyplus.com/browse/search) and search for the series you want to monitor.  
  Note: You need to be logged in for this.
  2. Click on the series from the search results to open its page.
  3. From the URL, copy the text after `entity-`. Example URL:
     ```txt
     https://www.disneyplus.com/browse/entity-fa6973b9-e7cf-49fb-81a2-d4908e4bf694
     ```
     Series ID: `fa6973b9-e7cf-49fb-81a2-d4908e4bf694`

  Add it like this:
  ```json
  {
    "zlo_disneyplus_monitor_series_id": {
      "fa6973b9-e7cf-49fb-81a2-d4908e4bf694": {}
    }
  }
  ```

  ### 4) Optional: tune ZLO Disney+ download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>Amazon Prime Video (ZLO)</summary>

  ### 1) Mount the ZLO binary and settings folder
  Place your `zlo7` binary at `./appdata/zlo/zlo7` (`zlo7` being the binary name) and your already-logged-in zlo7 `settings` folder content at `./appdata/zlo/config`.  
  The folder can be found at `C:\Users\<your username>\Documents\zlo7\settings` on Windows, or `~/Documents/zlo7/settings` on Linux.

  Then uncomment the **ZLO config** bind-mounts in `docker-compose.yaml`:
  ```yaml
  - ./appdata/zlo/zlo7:/app/appdata/bin/zlo/zlo7:rw
  - ./appdata/zlo/config:/home/mdnx-auto-dl/Documents/zlo7:rw
  ```

  ### 2) Enable Amazon (ZLO)
  Set [`ZLO_AMAZON_ENABLED`](config-options.md#ZLO_AMAZON_ENABLED) to `true` in `config.json`:
  ```json
  {
    "app": {
      "ZLO_AMAZON_ENABLED": true
    }
  }
  ```

  ### 3) Amazon series IDs to monitor
  Get the **series ID** from the Amazon Prime Video URL and add it under `zlo_amazon_monitor_series_id`.

  Add it like this:
  ```json
  {
    "zlo_amazon_monitor_series_id": {
      "your-amazon-series-id": {}
    }
  }
  ```

  ### 4) Optional: tune ZLO Amazon download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

---

## Start the container

```sh
docker compose up -d
```

That's it! The application will now keep track of the series you listed in `config.json`, automatically download new episodes as they're released, and update existing downloads whenever new dubs or subs become available.

---

## <a id="remote-specials-override"></a>Remote-specials override

Some recap, OVA, or compilation episodes may slip past the per-service detection because the upstream service does not label them in any way the detector can pick up on.  
The override file `remote-specials.yaml` at the root of this repo lists these episodes manually, and the running container fetches the file once per loop pass.

If you find one of these in your library:

1. Identify the upstream `series_id`, the upstream season number, and the upstream episode number. The container logs show these values when it parses each episode.
2. Open a PR adding an entry under the right downloader and service in `remote-specials.yaml`.
3. After the PR merges, every running container picks up the change on its next loop pass (usually within an hour. thx github cache).  
The matched episode is dropped at parse time and the rest of the episode numbers shift up.

If you maintain your own list, set the [`REMOTE_SPECIALS_URL`](config-options.md#REMOTE_SPECIALS_URL) environment variable in `docker-compose.yaml` to point at any HTTPS URL serving a file with the same shape. Set it to `false` to turn the feature off entirely.

After reading the instructions both here and/or in the `remote-specials.yaml` file, feel free to open a blank issue asking to add an episode to the blacklist.  
If you chose to open an issue instead of a PR, please include information like the specific episode and link to said episode on the streaming service, and I will add it to the list when I can.

For more advanced configuration options, please refer to the [configuration documentation](config-options.md).
