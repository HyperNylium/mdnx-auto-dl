# Get started with ZLO (Docker)

This guide sets up mdnx-auto-dl using **ZLO** (the `zlo7` binary) as the downloader for Crunchyroll, HiDive, and ADN.  
If you want to use multi-downloader-nx instead, or mix the two, see [mdnx-get-started.md](mdnx-get-started.md).

ZLO is a separate downloader from multi-downloader-nx. It uses its own `zlo7` binary and its own `.zlo7` config folder, and you sign in through the ZLO GUI. mdnx-auto-dl only runs the binary. It does not log you in.  
On startup it reads the ZLO storage database and will refuse to start a ZLO service if it cannot find a signed-in account in said DB. So you must already have a working `zlo7` binary and a signed-in `.zlo7` config folder before you begin.

### 1) Download `docker-compose.yaml` to your server
Save the [`docker-compose.yaml`](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/docker-compose.yaml) file:
```sh
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/docker-compose.yaml
```

### 2) Create required directories
```sh
mkdir -p ./appdata/logs
mkdir -p ./appdata/config
mkdir -p ./appdata/zlo/config
```

### 3) Get the zlo7 Linux CLI binary
ZLO7 is a paid tool, and you have to obtain the Linux CLI binary yourself from the developer.

- Join the [ZLO7 Discord server](https://discord.gg/AfMfWw7kHe).
- Contact the user named "ZLO7" to get details on how to pay and updates to the program.

If you have issues getting the binary, feel free to reach out to me either through a github issue or on my [Discord server](https://discord.gg/XAAfYJ5ABk).

### 4) Mount the zlo7 binary and config folder
Place your `zlo7` binary at `./appdata/zlo/zlo7` (`zlo7` being the binary name) and your already-signed-in ZLO `.zlo7` config folder content at `./appdata/zlo/config`. The `.zlo7` folder usually containes a `logs` and `storage` folder. Make sure both of them are in that `./appdata/zlo/config` folder.  
The `.zlo7` folder is created by the ZLO7 GUI and can be found at `C:\Users\<your username>\.zlo7` on Windows, or `~/.zlo7` on Linux. It must contain `storage/storage.db`, which is where ZLO keeps your sign-in.

Then uncomment the **ZLO config** bind-mounts in `docker-compose.yaml`:
```yaml
- ./appdata/zlo/zlo7:/app/appdata/bin/zlo/zlo7:rw
- ./appdata/zlo/config:/app/appdata/bin/zlo/config:rw
```

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
The config file has a top-level `destinations` section. Each provider you enable needs an entry that tells mdnx-auto-dl where to put finished files inside the container, and how to name the folders.

The shipped config already has one entry per provider, pointing at `/data/Anime` or `/data/TV Shows`. Both of those paths are mounted by the default `docker-compose.yaml`. If you only enable a few providers, you can delete the entries for the ones you do not use.

If you want to save files somewhere else on your host, change the **left** side of the bind-mount in `docker-compose.yaml` (for example, `./appdata/data/Anime` to `/mnt/chungus/Anime`) and keep the right side the same. If you want to change the right side (the path inside the container), update the matching `destinations.<service>.dir` in the config file too.

For the full list of variables you can use inside `folder_structure`, see [Options for `folder_structure`](config-options.md#options-for-folder_structure).

---

## Configure providers

<details>
  <summary>Crunchyroll (ZLO)</summary>

  ### 1) Enable Crunchyroll (ZLO)
  Set [`ZLO_CR_ENABLED`](config-options.md#ZLO_CR_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "ZLO_CR_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      ZLO_CR_ENABLED: true
  ```

  ### 2) Crunchyroll series IDs to monitor
  Get the **series ID** from the Crunchyroll URL and add it under `zlo_cr_monitor_series_id`.

  Example URL:
  ```txt
  https://www.crunchyroll.com/series/GG5H5XQ7D/kaiju-no-8
  ```
  Series ID: `GG5H5XQ7D`

  Add it like this:

  JSON:
  ```json
  {
    "zlo_cr_monitor_series_id": {
      "GG5H5XQ7D": {}
    }
  }
  ```
  YAML:
  ```yaml
  zlo_cr_monitor_series_id:
      "GG5H5XQ7D": {}
  ```

  ### 3) Optional: tune ZLO Crunchyroll download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>HiDive (ZLO)</summary>

  ### 1) Enable HiDive (ZLO)
  Set [`ZLO_HIDIVE_ENABLED`](config-options.md#ZLO_HIDIVE_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "ZLO_HIDIVE_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      ZLO_HIDIVE_ENABLED: true
  ```

  ### 2) HiDive series IDs to monitor
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

  JSON:
  ```json
  {
    "zlo_hidive_monitor_series_id": {
      "1050": {}
    }
  }
  ```
  YAML:
  ```yaml
  zlo_hidive_monitor_series_id:
      "1050": {}
  ```

  ### 3) Optional: tune ZLO HiDive download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>ADN (ZLO)</summary>

  ### 1) Enable ADN (ZLO)
  Set [`ZLO_ADN_ENABLED`](config-options.md#ZLO_ADN_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "ZLO_ADN_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      ZLO_ADN_ENABLED: true
  ```

  ### 2) ADN series IDs to monitor
  Get the **series ID** from the ADN URL and add it under `zlo_adn_monitor_series_id`.

  Add it like this:

  JSON:
  ```json
  {
    "zlo_adn_monitor_series_id": {
      "442": {}
    }
  }
  ```
  YAML:
  ```yaml
  zlo_adn_monitor_series_id:
      "442": {}
  ```

  ### 3) Optional: tune ZLO ADN download settings
  See the [ZLO per-service options](config-options.md#zlo-per-service-options) section for things like quality, dub languages, and subs.
</details>

---

## Start the container

```sh
docker compose up -d
```

That's it! mdnx-auto-dl will now keep track of the series you listed in your config file, automatically download new episodes as they're released, and update existing downloads whenever new dubs or subs become available.

---

## Next steps

Set up notifications, media-server refreshes, file organization, and more in the [how-to guides](guides/README.md). For the full picture, see [Next steps](get-started.md#next-steps) and the [Remote-specials override](get-started.md#remote-specials-override) in the main guide.
