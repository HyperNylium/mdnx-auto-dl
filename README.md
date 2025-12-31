# MDNX-auto-dl

[![Discord Server](https://discord.com/api/guilds/789034812799320074/widget.png?style=banner2)](https://discord.gg/XAAfYJ5ABk)

## Legal Warning
This application is not endorsed by or affiliated with *Crunchyroll*, *Hidive* or *AnimationDigitalNetwork*. This application enables you to download videos for offline viewing which may be forbidden by law in your country. The usage of this application may also cause a violation of the *Terms of Service* between you and the stream provider. This tool is not responsible for your actions; please make an informed decision before using this application.

# What is this?
MDNX-auto-dl is a free and open-source application that automatically downloads anime episodes from Crunchyroll and HiDive as they are released using [multi-downloader-nx](https://github.com/anidl/multi-downloader-nx)

# Get started
1. Save the [docker-compose.yaml](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/docker-compose.yaml) file to your server.
```
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/docker-compose.yaml
```

2. Make required directories.
```
mkdir -p ./appdata/logs
mkdir -p ./appdata/config
mkdir -p ./appdata/mdnx/widevine
mkdir -p ./appdata/mdnx/playready
mkdir -p ./appdata/mdnx/config
```

3. You need to add your CDM to the correct directory.

If you have a Widevine CDM, place your pair of `.bin` and `.pem` files, or single `.wvd` file into `./appdata/mdnx/widevine` and uncomment the Widivine bind-mount in `docker-compose.yaml`. \
For more information, refer to the get started guide's [Widevine section](https://github.com/anidl/multi-downloader-nx/blob/master/docs/GET-STARTED.md#widevine)

If you have a Playready CDM, place your pair of `bgroupcert.dat` and `zgpriv.dat` files, or single `.prd` into `./appdata/mdnx/playready`and uncomment the Playready bind-mount in `docker-compose.yaml`. \
For more information, refer to the get started guide's [Playready section](https://github.com/anidl/multi-downloader-nx/blob/master/docs/GET-STARTED.md#playready)

For legal reasons we do not include the CDM with the software, and you will have to source one yourself. Please do not open issues asking for these files. I can not give, nor instruct you on how to get these. Please Google around.

4. Save [config.json](https://github.com/HyperNylium/mdnx-auto-dl/blob/master/appdata/config/config.json) to `./appdata/config`
```
cd ./appdata/config
wget https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/appdata/config/config.json
```

5. Put in your Crunchyroll username and password into the following key-value pairs in `config.json`. You will be putting them in the `""` (quotes). \
Example:
```json
{
    "app": {
        "CR_ENABLED": true,
        "CR_USERNAME": "itsamemario@myemailprovider.com",
        "CR_PASSWORD": "thisismypassword123",
        ...
    }
}
```

Keep in mind that `CR_ENABLED` must be set to `true` for Crunchyroll's API to be used, which by default is set to `false`.

6. Get the series ID of the anime you want to monitor and put them into the `cr_monitor_series_id` list in `config.json`. \
Lets say you wanted to monitor Kaiju No. 8. You would go to the anime's page on Crunchyroll and copy the series ID from the URL. \
Example:
```
https://www.crunchyroll.com/series/GG5H5XQ7D/kaiju-no-8
```
The series ID would be `GG5H5XQ7D`.

You would then put it into the `cr_monitor_series_id` list in `config.json` like so:
```json
{
    "cr_monitor_series_id": {
        "GG5H5XQ7D": []
    },
    ...
}
```

7. Put in your HiDive username and password into the following key-value pairs in `config.json`. You will be putting them in the `""` (quotes). \
Example:
```json
{
    "app": {
        "HIDIVE_ENABLED": true,
        "HIDIVE_USERNAME": "itsamemario@myemailprovider.com",
        "HIDIVE_PASSWORD": "thisismypassword123",
        ...
    }
}
```

Keep in mind that `HIDIVE_ENABLED` must be set to `true` for HiDive's API to be used, which by default is set to `false`.

8. Get the series ID of the anime you want to monitor and put them into the `hidive_monitor_series_id` list in `config.json`. \
Lets say you wanted to monitor Call of the night. You need to:
 - 1. Go to [HiDive's search site](https://www.hidive.com/search). No login required.
 - 2. Click on the "Filter" button and select "Series" under "Content".
 - 3. Search for what you want to monitor. In this case "Call of the night".
 - 4. After clicking on the search result, you will be taken to the anime's page. The URL will look something like this:

```
https://www.hidive.com/season/19079?seriesId=1050
```
The series ID would be `1050`.

You would then put it into the `hidive_monitor_series_id` list in `config.json` like so:
```json
{
    "hidive_monitor_series_id": {
        "1050": []
    },
    ...
}
```

8. Start the container
```
docker compose up -d
```

That’s it! The application will now keep track of the series you listed in config.json, automatically download new episodes as they’re released, and update existing downloads whenever new dubs or subs become available.

# Future plans
You can track progress of things [here](https://github.com/users/HyperNylium/projects/4)

# Acknowledgments
**This project would not be possible without the following third-party tools/packages:**

[Multi-downloader-nx](https://github.com/anidl/multi-downloader-nx)

[FFmpeg](https://ffmpeg.org/)

[MKVToolNix](https://mkvtoolnix.download/)

[Bento4-SDK](https://www.bento4.com/)

# License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
