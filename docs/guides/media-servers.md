# How-to: Refresh Plex and Jellyfin

After mdnx-auto-dl saves a new episode, it can tell your media server to rescan so the episode shows up without waiting for a scheduled scan.  
You can set up **Plex**, **Jellyfin**, or **both** at the same time.

- If [`PLEX_URL`](../config-options.md#PLEX_URL) is `null` (default), Plex is not notified.
- If [`JELLY_URL`](../config-options.md#JELLY_URL) is `null` (default), Jellyfin is not notified.

All keys below live in the `app` section of your config file.

---

## Plex

Set [`PLEX_URL`](../config-options.md#PLEX_URL) in your config file:

JSON:
```json
"app": {
    "PLEX_URL": "http://192.168.1.10:32400"
}
```
YAML:
```yaml
app:
    PLEX_URL: "http://192.168.1.10:32400"
```

After running `docker compose up -d && docker compose logs -f`, you will see a log line like this:
```txt
Open this URL in a browser to authorize the app:
https://app.plex.tv/auth#?blablablablablablablabla
```

Open that URL in a browser, log in to your Plex account, and authorize the app. The application then saves the Plex token to [`PLEX_TOKEN`](../config-options.md#PLEX_TOKEN) automatically and continues startup. There is no need to set `PLEX_TOKEN` by hand. The auth window is 10 minutes. If you do not authorize within that time, the application will exit.

After you authorize the app, you should see this in the logs:
```txt
Authorization completed. Token stored.
User is authenticated. Testing library scan...
Scan triggered successfully.
Library scan successful.
...
```

You will not have to do the authorization step again unless you delete `PLEX_TOKEN` or remove the session from Authenticated Devices in your Plex account settings.

**Keys:** [`PLEX_URL`](../config-options.md#PLEX_URL) [`PLEX_TOKEN`](../config-options.md#PLEX_TOKEN) [`PLEX_URL_OVERRIDE`](../config-options.md#PLEX_URL_OVERRIDE)

---

## Jellyfin

Set [`JELLY_URL`](../config-options.md#JELLY_URL) and [`JELLY_API_KEY`](../config-options.md#JELLY_API_KEY):

JSON:
```json
"app": {
    "JELLY_URL": "http://192.168.1.10:8096",
    "JELLY_API_KEY": "your-jellyfin-api-key"
}
```
YAML:
```yaml
app:
    JELLY_URL: "http://192.168.1.10:8096"
    JELLY_API_KEY: "your-jellyfin-api-key"
```

There is no manual authorization step like Plex. Make sure your API key is correct and you should be good to go.

**Keys:** [`JELLY_URL`](../config-options.md#JELLY_URL) [`JELLY_API_KEY`](../config-options.md#JELLY_API_KEY) [`JELLY_URL_OVERRIDE`](../config-options.md#JELLY_URL_OVERRIDE)

---

## Refreshing only one library

By default, if you only set:
- [`PLEX_URL`](../config-options.md#PLEX_URL) (and authorize once to populate [`PLEX_TOKEN`](../config-options.md#PLEX_TOKEN)), and/or
- [`JELLY_URL`](../config-options.md#JELLY_URL) + [`JELLY_API_KEY`](../config-options.md#JELLY_API_KEY)

the application refreshes **all libraries** on the configured server(s).

To refresh only a specific library, set the matching `*_URL_OVERRIDE` to `true` and set the matching `*_URL` to the exact refresh endpoint for that one library.

### Plex override

Refresh everything (default):
```json
"app": {
    "PLEX_URL": "http://192.168.1.10:32400",
    "PLEX_URL_OVERRIDE": false
}
```

Refresh only one library:
```json
"app": {
    "PLEX_URL": "http://192.168.1.10:32400/library/sections/1/refresh",
    "PLEX_URL_OVERRIDE": true
}
```
YAML:
```yaml
app:
    PLEX_URL: "http://192.168.1.10:32400/library/sections/1/refresh"
    PLEX_URL_OVERRIDE: true
```

Where `1` in `/library/sections/1/refresh` is the library key you want to refresh.  
Find the library key by running `curl http://<YOUR_SERVER_IP>:32400/library/sections` and looking for `key="X"` in the output.

### Jellyfin override

Refresh everything (default):
```json
"app": {
    "JELLY_URL": "http://192.168.1.10:8096",
    "JELLY_URL_OVERRIDE": false
}
```

Refresh only one library:
```json
"app": {
    "JELLY_URL": "http://192.168.1.10:8096/Items/123456abcdef/Refresh?Recursive=true",
    "JELLY_API_KEY": "blablablablablablabla",
    "JELLY_URL_OVERRIDE": true
}
```
YAML:
```yaml
app:
    JELLY_URL: "http://192.168.1.10:8096/Items/123456abcdef/Refresh?Recursive=true"
    JELLY_API_KEY: "blablablablablablabla"
    JELLY_URL_OVERRIDE: true
```

Where `123456abcdef` in `/Items/123456abcdef/Refresh?Recursive=true` is the ID of the library you want to refresh.  
Find the ID by running `curl http://<YOUR_SERVER_IP>:8096/Users/<USER_ID>/Views?api_key=<YOUR_API_KEY>` and looking for `Id` in the output.  
Find your `USER_ID` by running `curl http://<YOUR_SERVER_IP>:8096/Users?api_key=<YOUR_API_KEY>` and looking for `Id` in the output.
