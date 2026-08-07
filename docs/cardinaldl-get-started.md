# Get started with CardinalDL (Docker)

This guide sets up mdnx-auto-dl using **CardinalDL** (the `cardinaldl` binary) as the downloader for Crunchyroll, HiDive, ADN, Disney, Netflix, and Amazon.  
If you want to use multi-downloader-nx instead, or mix the two, see [mdnx-get-started.md](mdnx-get-started.md).

CardinalDL is a separate downloader from multi-downloader-nx. It uses its own `cardinaldl` binary and its own `.cardinaldl` config folder, and you sign in through the CardinalDL GUI or CLI. mdnx-auto-dl only runs the binary. It does not log you in.

On startup it reads the CardinalDL storage database and will refuse to start a CardinalDL service unless it finds a signed-in account, a device id, and a device proof key that this machine can actually read.

If you copied your `.cardinaldl` folder over from a Windows machine, the device key in it is locked to that Windows account and cannot be unlocked on Linux. The app will tell you so and stop. Fix it by logging in again on the Linux side:

```bash
./cardinaldl --login --username "your_provided_CDL_username" --password "your_provided_CDL_password"
```

Run that against the same config folder you bind-mount, then start the container again.

So you must already have a working `cardinaldl` binary and a signed-in `.cardinaldl` config folder before you begin.

### 1) Download `docker-compose.yaml` to your server
Save the [`docker-compose.yaml`](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/docker-compose.yaml) file:
```sh
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/docker-compose.yaml
```

### 2) Create required directories
```sh
mkdir -p ./appdata/logs
mkdir -p ./appdata/config
mkdir -p ./appdata/cardinaldl/config
```

### 3) Get the cardinaldl Linux CLI binary
CardinalDL is a paid tool, and you have to obtain the Linux CLI binary yourself from the developer.

- Join the [CardinalDL Discord server](https://discord.gg/AfMfWw7kHe).
- Contact the user named "CDL" to get details on how to pay and updates to the program.

If you have issues getting the binary, feel free to reach out to me either through a github issue or on my [Discord server](https://discord.gg/XAAfYJ5ABk).

### 4) Mount the cardinaldl binary and config folder
Place your `cardinaldl` binary at `./appdata/cardinaldl/cardinaldl` (`cardinaldl` being the binary name) and your already-signed-in CardinalDL `.cardinaldl` config folder content at `./appdata/cardinaldl/config`. The `.cardinaldl` folder usually containes a `logs` and `storage` folder. Make sure both of them are in that `./appdata/cardinaldl/config` folder.  
The `.cardinaldl` folder is created by the CardinalDL GUI and can be found at `C:\Users\<your username>\.cardinaldl` on Windows, or `~/.cardinaldl` on Linux. It must contain `storage/storage.db`, which is where CardinalDL keeps your sign-in.

Then uncomment the **CardinalDL config** bind-mounts in `docker-compose.yaml`:
```yaml
- ./appdata/cardinaldl/cardinaldl:/app/appdata/bin/cardinaldl/cardinaldl:rw
- ./appdata/cardinaldl/config:/app/appdata/bin/cardinaldl/config:rw
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
  <summary>Crunchyroll (CardinalDL)</summary>

  ### 1) Enable Crunchyroll (CardinalDL)
  Set [`CDL_CR_ENABLED`](config-options.md#CDL_CR_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "CDL_CR_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CDL_CR_ENABLED: true
  ```

  ### 2) Crunchyroll series IDs to monitor
  Get the **series ID** from the Crunchyroll URL and add it under `cdl_cr_monitor_series_id`.

  Example URL:
  ```txt
  https://www.crunchyroll.com/series/GG5H5XQ7D/kaiju-no-8
  ```
  Series ID: `GG5H5XQ7D`

  Add it like this:

  JSON:
  ```json
  {
    "cdl_cr_monitor_series_id": {
      "GG5H5XQ7D": {}
    }
  }
  ```
  YAML:
  ```yaml
  cdl_cr_monitor_series_id:
      "GG5H5XQ7D": {}
  ```

  ### 3) Optional: tune CardinalDL Crunchyroll download settings
  See the [CardinalDL per-service options](config-options.md#cardinaldl-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>HiDive (CardinalDL)</summary>

  ### 1) Enable HiDive (CardinalDL)
  Set [`CDL_HIDIVE_ENABLED`](config-options.md#CDL_HIDIVE_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "CDL_HIDIVE_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CDL_HIDIVE_ENABLED: true
  ```

  ### 2) HiDive series IDs to monitor
  Get the **series ID** from HiDive and add it under `cdl_hidive_monitor_series_id`.

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
    "cdl_hidive_monitor_series_id": {
      "1050": {}
    }
  }
  ```
  YAML:
  ```yaml
  cdl_hidive_monitor_series_id:
      "1050": {}
  ```

  ### 3) Optional: tune CardinalDL HiDive download settings
  See the [CardinalDL per-service options](config-options.md#cardinaldl-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>ADN (CardinalDL)</summary>

  ### 1) Enable ADN (CardinalDL)
  Set [`CDL_ADN_ENABLED`](config-options.md#CDL_ADN_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "CDL_ADN_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CDL_ADN_ENABLED: true
  ```

  ### 2) ADN series IDs to monitor
  Get the **series ID** from the ADN URL and add it under `cdl_adn_monitor_series_id`.

  Add it like this:

  JSON:
  ```json
  {
    "cdl_adn_monitor_series_id": {
      "442": {}
    }
  }
  ```
  YAML:
  ```yaml
  cdl_adn_monitor_series_id:
      "442": {}
  ```

  ### 3) Optional: tune CardinalDL ADN download settings
  See the [CardinalDL per-service options](config-options.md#cardinaldl-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>Disney (CardinalDL)</summary>

  ### 1) Enable Disney (CardinalDL)
  Set [`CDL_DISNEY_ENABLED`](config-options.md#CDL_DISNEY_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "CDL_DISNEY_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CDL_DISNEY_ENABLED: true
  ```

  ### 2) Disney series IDs to monitor
  Get the **series ID** from the Disney URL and add it under `cdl_disney_monitor_series_id`.

  Add it like this:

  JSON:
  ```json
  {
    "cdl_disney_monitor_series_id": {
      "<series id>": {}
    }
  }
  ```
  YAML:
  ```yaml
  cdl_disney_monitor_series_id:
      "<series id>": {}
  ```

  ### 3) Optional: tune CardinalDL Disney download settings
  See the [CardinalDL per-service options](config-options.md#cardinaldl-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>Netflix (CardinalDL)</summary>

  ### 1) Enable Netflix (CardinalDL)
  Set [`CDL_NETFLIX_ENABLED`](config-options.md#CDL_NETFLIX_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "CDL_NETFLIX_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CDL_NETFLIX_ENABLED: true
  ```

  ### 2) Netflix series IDs to monitor
  Get the **series ID** from the Netflix URL and add it under `cdl_netflix_monitor_series_id`.

  Add it like this:

  JSON:
  ```json
  {
    "cdl_netflix_monitor_series_id": {
      "<series id>": {}
    }
  }
  ```
  YAML:
  ```yaml
  cdl_netflix_monitor_series_id:
      "<series id>": {}
  ```

  ### 3) Optional: tune CardinalDL Netflix download settings
  See the [CardinalDL per-service options](config-options.md#cardinaldl-per-service-options) section for things like quality, dub languages, and subs.
</details>

<details>
  <summary>Amazon (CardinalDL)</summary>

  ### 1) Enable Amazon (CardinalDL)
  Set [`CDL_AMAZON_ENABLED`](config-options.md#CDL_AMAZON_ENABLED) to `true` in your config file:

  JSON:
  ```json
  {
    "app": {
      "CDL_AMAZON_ENABLED": true
    }
  }
  ```
  YAML:
  ```yaml
  app:
      CDL_AMAZON_ENABLED: true
  ```

  ### 2) Amazon series IDs to monitor
  Get the **series ID** from the Amazon URL and add it under `cdl_amazon_monitor_series_id`.

  Add it like this:

  JSON:
  ```json
  {
    "cdl_amazon_monitor_series_id": {
      "<series id>": {}
    }
  }
  ```
  YAML:
  ```yaml
  cdl_amazon_monitor_series_id:
      "<series id>": {}
  ```

  ### 3) Optional: tune CardinalDL Amazon download settings
  See the [CardinalDL per-service options](config-options.md#cardinaldl-per-service-options) section for things like quality, dub languages, and subs.
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
