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
mkdir -p ./appdata/mdnx/widevine
mkdir -p ./appdata/mdnx/playready
mkdir -p ./appdata/mdnx/config
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

For legal reasons we do not include the CDM with the software, and you will have to source one yourself. Please do not open issues asking for these files. I can not give, nor instruct you on how to get these. Please Google around.

### 4) Download `config.json` into `./appdata/config`
Save [`config.json`](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/appdata/config/config.json) to `./appdata/config`:
```sh
cd ./appdata/config
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/appdata/config/config.json
```

---

## Configure providers

### 5) Crunchyroll credentials
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

Keep in mind that `CR_ENABLED` must be set to `true` for Crunchyroll's API to be used, which by default is set to `false`.

### 6) Crunchyroll series IDs to monitor
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
    "GG5H5XQ7D": []
  }
}
```

### 7) HiDive credentials
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

Keep in mind that `HIDIVE_ENABLED` must be set to `true` for HiDive's API to be used, which by default is set to `false`.

### 8) HiDive series IDs to monitor
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
    "1050": []
  }
}
```

---

## Run

### 9) Start the container
```sh
docker compose up -d
```

That’s it! The application will now keep track of the series you listed in `config.json`, automatically download new episodes as they’re released, and update existing downloads whenever new dubs or subs become available.

For more advanced configuration options using the `config.json`, please refer to the [configuration documentation](config-options.md).
