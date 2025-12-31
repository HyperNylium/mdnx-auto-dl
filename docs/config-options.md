## Notes for `config.json` usage

### Where keys go
- Anything listed in the **Config** column in the table below goes under the `app` section.
- **Exception:** `cr_monitor_series_id` and `hidive_monitor_series_id` are in the **global scope** of the JSON file (not under `app` or `mdnx`).

Example: setting `CR_USERNAME` under `app`:
```json
{
  "app": {
    "CR_USERNAME": ""
  }
}
```

### Passing options through to `multi-downloader-nx`
If you want to modify values such as `q: 0` and `dubLang: ["jpn", "eng", "zho"]` in `cli-defaults.yml` for multi-downloader-nx, you only need to modify the `mdnx` key.

Any setting from [multi-downloader-nx's documentation](https://github.com/anidl/multi-downloader-nx/blob/master/docs/DOCUMENTATION.md) is valid as long as the option has a `cli-default Entry` section that isn't `NaN`:
```json
{
  "mdnx": {
    "q": 0,
    "dubLang": ["jpn", "eng", "zho"]
  }
}
```

### JSON formatting rules
Standard JSON formatting still applies:
- Separate list items with `,` (comma)
- Integers are plain numbers (not quoted)
- Anything in quotes is a string

If you choose to not include key-value pairs that you don't modify in `config.json`, the application will use the default values listed in the table below.

---

## Config options for `config.json`

| Config                             | Default value                                                                  | Type          | Explanation                                                                                                                                                      |
| :--------------------------------- | :---------------------------------------------------------------------------: | :-----------: | :---------------------------------------------------------------------------------------------------------------------------------------------------------------  |
| `cr_monitor_series_id`             | `[]`                                                                          | array         | List of Crunchyroll series IDs to watch for new episode releases and dub/sub updates on already existing episodes.                                                |
| `hidive_monitor_series_id`         | `[]`                                                                          | array         | List of HiDive series IDs to watch for new episode releases and dub/sub updates on already existing episodes.                                                     |
| `TEMP_DIR`                         | `/app/appdata/temp`                                                           | string        | Temporary staging directory. Raw downloads are written here before moving into your library.                                                                      |
| `BIN_DIR`                          | `/app/appdata/bin`                                                            | string        | Path containing bundled binaries (e.g. `multi-download-nx`, `Bento4-SDK`) inside the container.                                                                   |
| `LOG_DIR`                          | `/app/appdata/logs`                                                           | string        | Folder where active and archived logs are stored.                                                                                                                 |
| `DATA_DIR`                         | `/data`                                                                       | string        | Root of your anime library on the host. Finished files are organized here according to `FOLDER_STRUCTURE`.                                                        |
| `CR_ENABLED`                       | `false`                                                                       | boolean       | When `true`, enable auth with CR_MDNX_API and download any series IDs in `cr_monitor_series_id`.                                                                  |
| `CR_USERNAME`                      | `""`                                                                          | string        | Crunchyroll username for authentication.                                                                                                                          |
| `CR_PASSWORD`                      | `""`                                                                          | string        | Crunchyroll password for authentication.                                                                                                                          |
| `HIDIVE_ENABLED`                   | `false`                                                                       | boolean       | When `true`, enable auth with HIDIVE_MDNX_API and download any series IDs in `hidive_monitor_series_id`.                                                          |
| `HIDIVE_USERNAME`                  | `""`                                                                          | string        | HiDive username for authentication.                                                                                                                               |
| `HIDIVE_PASSWORD`                  | `""`                                                                          | string        | HiDive password for authentication.                                                                                                                               |
| `BACKUP_DUBS`                      | `["zho"]`                                                                     | array         | List of backup dubs to download if the primary dubs are not available.                                                                                            |
| `FOLDER_STRUCTURE`                 | `${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}`| string        | Template for how seasons and episodes are laid out under `DATA_DIR`.                                                                                              |
| `CHECK_MISSING_DUB_SUB`            | `true`                                                                        | boolean       | When `true`, detect and report episodes missing dub or subtitle tracks.                                                                                           |
| `CHECK_MISSING_DUB_SUB_TIMEOUT`    | `300`                                                                         | number        | Seconds to wait before timing out when checking for missing dubs/subs on a file.                                                                                  |
| `CHECK_FOR_UPDATES_INTERVAL`       | `3600`                                                                        | number        | Seconds to wait between complete library scans for new episodes or missing tracks.                                                                                |
| `BETWEEN_EPISODE_DL_WAIT_INTERVAL` | `30`                                                                          | number        | Delay in seconds after each episode download to reduce API rate-limiting.                                                                                         |
| `CR_FORCE_REAUTH`                  | `false`                                                                       | boolean       | When `true`, always perform a fresh Crunchyroll login and overwrite `cr_token.yml`, then reset to `false`.                                                        |
| `CR_SKIP_API_TEST`                 | `false`                                                                       | boolean       | When `true`, skip the startup self-test that probes the Crunchyroll API.                                                                                          |
| `HIDIVE_FORCE_REAUTH`              | `false`                                                                       | boolean       | When `true`, always perform a fresh HiDive login and overwrite `hd_new_token.yml`, then reset to `false`.                                                         |
| `HIDIVE_SKIP_API_TEST`             | `false`                                                                       | boolean       | When `true`, skip the startup self-test that probes the HiDive API.                                                                                               |
| `ONLY_CREATE_QUEUE`                | `false`                                                                       | boolean       | When `true`, only create/update `queue.json` without downloading anything. Will exit with code 0 after it's done.                                                 |
| `SKIP_QUEUE_REFRESH`               | `false`                                                                       | boolean       | When `true`, skip refreshing the `queue.json` file, and go into mainloop with whatever data currently exists.                                                     |
| `DRY_RUN`                          | `false`                                                                       | boolean       | When `true`, simulate downloads without actually downloading any files. Useful for testing configuration.                                                         |
| `LOG_LEVEL`                        | `info`                                                                        | string        | Set the logging level. Options: `debug`, `info`, `warning`, `error`, `critical`.                                                                                  |
| `NOTIFICATION_PREFERENCE`          | `none`                                                                        | string        | Set what service you want to use to receive notifications. Options: `none`, `smtp`, `ntfy`.                                                                       |
| `NTFY_SCRIPT_PATH`                 | `/app/appdata/config/ntfy.sh`                                                 | string        | Path to the ntfy.sh script inside the container. Only needed if `NOTIFICATION_PREFERENCE` is set to `ntfy`.                                                       |
| `SMTP_FROM`                        | `""`                                                                          | string        | Email address that notifications are sent from. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                                                        |
| `SMTP_TO`                          | `""`                                                                          | string/array  | Email address that notifications are sent to. Also supports a list of emails. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                          |
| `SMTP_HOST`                        | `""`                                                                          | string        | SMTP server hostname. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                                                                                  |
| `SMTP_USERNAME`                    | `""`                                                                          | string        | SMTP username. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                                                                                         |
| `SMTP_PASSWORD`                    | `""`                                                                          | string        | SMTP password. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                                                                                         |
| `SMTP_PORT`                        | `587`                                                                         | number        | SMTP server port. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                                                                                      |
| `SMTP_STARTTLS`                    | `true`                                                                        | boolean       | When `true`, use STARTTLS for SMTP connections. Only needed if `NOTIFICATION_PREFERENCE` is set to `smtp`.                                                        |
| `PLEX_URL`                         | `null`                                                                        | string        | URL of the Plex server to notify. Must be the complete URL of your server. Example: `http://192.168.1.10:32400`.                                                  |
| `PLEX_TOKEN`                       | `null`                                                                        | string        | Plex auth token. You normally do not need to set this manually; it is saved automatically after you authorize the app (check the logs on first boot!).            |
| `PLEX_URL_OVERRIDE`                | `false`                                                                       | boolean       | When `true`, use the Plex library refresh URL exactly as provided in `PLEX_URL` (e.g. a single-library refresh endpoint).                                         |
| `JELLY_URL`                        | `null`                                                                        | string        | URL of the Jellyfin server to notify. Must be the complete URL of your server. Example: `http://192.168.1.10:8096`.                                               |
| `JELLY_API_KEY`                    | `null`                                                                        | string        | Jellyfin API key.                                                                                                                                                 |
| `JELLY_URL_OVERRIDE`               | `false`                                                                       | boolean       | When `true`, use the Jellyfin library refresh URL exactly as provided in `JELLY_URL` (e.g. a single-library refresh endpoint).                                    |

---

## Options for `FOLDER_STRUCTURE`

| Variable           | Example value                | Explanation |
| :----------------- | :--------------------------: | :---------- |
| `${seriesTitle}`   | `Kaiju No. 8`                | Sanitized series title (filesystem-unsafe characters replaced). |
| `${season}`        | `1`                          | Season number, no leading zeros. |
| `${seasonPadded}`  | `01`                         | Season number padded to two digits. |
| `${episode}`       | `1`                          | Episode number, no leading zeros. |
| `${episodePadded}` | `01`                         | Episode number padded to two digits. |
| `${episodeName}`   | `The Man Who Became a Kaiju` | Sanitized episode title. |

Example of `FOLDER_STRUCTURE` with the above variables:
```txt
${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}
```

This would result in the following folder structure:
```txt
Kaiju No. 8/S1/Kaiju No. 8 - S01E01
```

---

## Options for `NOTIFICATION_PREFERENCE`

| Option | Explanation |
| :----- | :---------- |
| `none` | No notifications will be sent. |
| `smtp` | Send notifications via SMTP email. Requires additional configuration in `config.json`. |
| `ntfy` | Send notifications via ntfy.sh. Requires additional configuration in `config.json` and `app/appdata/config/ntfy.sh`. |

### SMTP (`NOTIFICATION_PREFERENCE: "smtp"`)
Add the following key-value pairs to `config.json` right under the `NOTIFICATION_PREFERENCE` key:
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

`SMTP_TO` can also be a list of email addresses if you want to send to multiple people like this:
```json
"SMTP_TO": ["whowesendingto@gmail.com", "whoelsewesendingto@domain.com"]
```

### ntfy (`NOTIFICATION_PREFERENCE: "ntfy"`)
Add the following key-value pairs to `config.json` right under the `NOTIFICATION_PREFERENCE` key:
```json
"NOTIFICATION_PREFERENCE": "ntfy",
"NTFY_SCRIPT_PATH": "/app/appdata/config/ntfy.sh"
```

Make sure to set `NTFY_URL` in `appdata/config/ntfy.sh` to the URL of your ntfy server.  
To modify things like tags and such, you can modify the `ntfy.sh` script.  
You would also need a bind-mount like: `./appdata/config/ntfy.sh:/app/appdata/config/ntfy.sh`

---

## Media server options (Plex and Jellyfin)

You can configure **Plex**, **Jellyfin**, or **both** at the same time.

- If `PLEX_URL` is `null` (default), Plex will not be notified.
- If `JELLY_URL` is `null` (default), Jellyfin will not be notified.

### Plex (`PLEX_URL`)
Make sure your `config.json` has the following key-value pairs:
```json
{
  "app": {
    "PLEX_URL": "http://<YOUR_SERVER_IP>:32400"
  }
}
```

Where `<YOUR_SERVER_IP>` is the IP address of your Plex server.

After doing `docker compose up -d && docker compose logs -f`, you will see a log line like this:
```txt
Open this URL in a browser to authorize the app:
https://app.plex.tv/auth#?blablablablablablablabla
```

Open that URL in a browser, login to your Plex account, and authorize the app.  
Once you do that, the application will save the Plex token to the `PLEX_TOKEN` variable automatically and continue to start up.  
If the `PLEX_TOKEN` variable doesn't exist, it will create it and store the token. There is no need to manually define `PLEX_TOKEN` in your `config.json`.  
The timeout for auth is 10 minutes. If you don't authorize the app within that time, the application will exit.

After you authorize the app, you should see this in the logs:
```txt
Authorization completed. Token stored.
User is authenticated. Testing library scan...
Scan triggered successfully.
Library scan successful.
...
```

If so, you're all set!  
You will not have to do the authorization step again unless you delete the `PLEX_TOKEN` variable or delete the session from Authenticated Devices in your Plex account settings.

### Jellyfin (`JELLY_URL` + `JELLY_API_KEY`)
Make sure your `config.json` has the following key-value pairs:
```json
{
  "app": {
    "JELLY_URL": "http://<YOUR_SERVER_IP>:8096",
    "JELLY_API_KEY": "<YOUR_API_KEY>"
  }
}
```

Where `<YOUR_SERVER_IP>` is the IP address of your Jellyfin server and `<YOUR_API_KEY>` is your Jellyfin API key.  
There is no manual authorization step like Plex. Just make sure your API key is correct, and you should be good to go!

---

## Options for `PLEX_URL_OVERRIDE` and `JELLY_URL_OVERRIDE`

By default, if you only set:
- `PLEX_URL` (and authorize once to populate `PLEX_TOKEN`), and/or
- `JELLY_URL` + `JELLY_API_KEY`

The application will try to refresh **all libraries** on the configured server(s).

If you want to only refresh a specific library, set the relevant `*_URL_OVERRIDE` to `true` and set the corresponding `*_URL` to the exact refresh endpoint for that one library.

### Plex override (`PLEX_URL_OVERRIDE`)
The usual config that will refresh everything:
```json
"PLEX_URL": "http://192.168.1.10:32400",
"PLEX_URL_OVERRIDE": false
```

With `PLEX_URL_OVERRIDE` enabled for only scanning 1 library:
```json
"PLEX_URL": "http://192.168.1.10:32400/library/sections/1/refresh",
"PLEX_URL_OVERRIDE": true
```

Where `1` in `/library/sections/1/refresh` is the library key you want to refresh.  
You can find the library key by running `curl http://<YOUR_SERVER_IP>:32400/library/sections` and look for the `key="X"` in the output.

### Jellyfin override (`JELLY_URL_OVERRIDE`)
The usual config that will refresh everything:
```json
"JELLY_URL": "http://192.168.1.10:8096",
"JELLY_URL_OVERRIDE": false
```

With `JELLY_URL_OVERRIDE` enabled for only scanning 1 library:
```json
"JELLY_URL": "http://192.168.1.10:8096/Items/123456abcdef/Refresh?Recursive=true",
"JELLY_API_KEY": "blablablablablablabla",
"JELLY_URL_OVERRIDE": true
```

Where `123456abcdef` in `/Items/123456abcdef/Refresh?Recursive=true` is the ID of the library you want to refresh.  
You can find the ID by running `curl http://<YOUR_SERVER_IP>:8096/Users/<USER_ID>/Views?api_key=<YOUR_API_KEY>` and look for the `Id` in the output.  
You can find your `USER_ID` by running `curl http://<YOUR_SERVER_IP>:8096/Users?api_key=<YOUR_API_KEY>` and look for the `Id` in the output.

---

## How to blacklist entire seasons or just specific episodes

This is great for when you want to skip downloading certain seasons or episodes from a series you are monitoring.  
An example use case is that you only want to download the simulcast season of One Piece, and skip all the other seasons.

First, the migration of the `cr_monitor_series_id` and `hidive_monitor_series_id` from an array to an object needs to be done.  
If this is your first time setting up mdnx-auto-dl, you can skip this step and just use the new format below.

Format would go from:
```json
{
  "cr_monitor_series_id": [
    "GQWH0M1J3",
    "GT00362335"
  ]
}
```

To this. Doing this means it will download all episodes in the series, since nothing is blacklisted in the `[]` array for each series ID:
```json
{
  "cr_monitor_series_id": {
    "GQWH0M1J3": [],
    "GT00362335": []
  }
}
```

You would blacklist an entire season like this:
```json
{
  "cr_monitor_series_id": {
    "GQWH0M1J3": ["S:GYE5CQNJ2"],
    "GT00362335": ["S:GS00362336JAJP"]
  }
}
```

Where `GYE5CQNJ2` and `GS00362336JAJP` are the season IDs you want to blacklist from downloading.  
This will skip downloading all episodes from those seasons.

You would blacklist an episode from a season like this:
```json
{
  "cr_monitor_series_id": {
    "GQWH0M1J3": ["S:GYE5CQNJ2:E:3"],
    "GT00362335": ["S:GS00362336JAJP:E:6"]
  }
}
```

Where `3` and `6` are the episode numbers you want to blacklist from downloading in those seasons.  
This will skip downloading only episode 3 from season `GYE5CQNJ2`, and only episode 6 from season `GS00362336JAJP`.

Or multiple episodes from a season like this:
```json
{
  "cr_monitor_series_id": {
    "GQWH0M1J3": ["S:GYE5CQNJ2:E:1-3"],
    "GT00362335": ["S:GS00362336JAJP:E:1-5"]
  }
}
```

Where `1-3` and `1-5` are the episode ranges you want to blacklist from downloading in those seasons.  
This will skip downloading episodes between 1 and 3 (inclusive) from season `GYE5CQNJ2`, and episodes between 1 and 5 (inclusive) from season `GS00362336JAJP`.

Can of course blacklist multiple seasons/episodes as well:
```json
{
  "cr_monitor_series_id": {
    "GQWH0M1J3": [
      "S:GYE5CQNJ2",
      "S:blablabla",
      "S:blablablaaa:E:1-3"
    ],
    "GT00362335": ["S:GS00362336JAJP"]
  }
}
```

Blacklisting a season/episode(s) from downloading will still generate the `queue.json` data for the series.  
All this does is set `episode_skip` to `true` and in the download process, it checks whether or not that boolean is true (skip it) or false (download it, if not already downloaded).

---

## Environment variables

These are the environment variables that you can set in the `docker-compose.yaml` file under the `environment` section.

| Variable      | Default value                                                                                                              | Explanation |
| :------------ | :------------------------------------------------------------------------------------------------------------------------ | :---------- |
| `UID`         | `1000`                                                                                                                    | User ID that mdnx-auto-dl will run as. |
| `GID`         | `1000`                                                                                                                    | Group ID that mdnx-auto-dl will run as. |
| `TZ`          | `America/New_York`                                                                                                        | Timezone for the container. Set to your local timezone from the "TZ identifier" column [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). |
| `CONFIG_FILE` | `/app/appdata/config/config.json`                                                                                         | `config.json` file location in the container. |
| `QUEUE_FILE`  | `/app/appdata/config/queue.json`                                                                                          | `queue.json` file location in the container. |
| `BENTO4_URL`  | `https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/Bento4-SDK.zip`             | URL for downloading `Bento4-SDK.zip` if both the file itself and extracted folder doesn't exist. |
| `MDNX_URL`    | `https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/mdnx.zip`                   | URL for downloading `mdnx.zip` if both the file itself and extracted folder doesn't exist. |
