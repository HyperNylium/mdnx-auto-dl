import os
import sys
import signal

from appdata.modules.MainLoop import MainLoop
from appdata.modules.Globals import file_manager, log_manager
from appdata.modules.MediaServerManager import mediaserver_auth, mediaserver_scan_library
from appdata.modules.API.MDNX._shared import (
    MDNX_SERVICE_CR_TOKEN_PATH, MDNX_SERVICE_HIDIVE_TOKEN_PATH, MDNX_SERVICE_ADN_TOKEN_PATH,
    MDNX_SERVICE_PLAYREADY_PATH, MDNX_SERVICE_WIDEVINE_PATH,
    update_mdnx_config
)
from appdata.modules.API.ZLO7._shared import (
    ZLO_SERVICE_BIN_PATH, ZLO_SERVICE_CONFIG_SETTINGS_PATH
)
from appdata.modules.Vars import (
    config,
    APP_VERSION, JELLY_CONFIGURED, MDNX_ENABLED, PLEX_CONFIGURED, SERVICES, ZLO_ENABLED,
    get_running_user, handle_exception, output_effective_config, update_app_config, validate_cdm, validate_destinations
)


def app():

    if not MDNX_ENABLED and not ZLO_ENABLED:
        log_manager.warning("No services are enabled. Please enable at least one MDNX or ZLO service in your config to use this application.")
        sys.exit(0)

    # can we reliably read/write to the destination directory?
    if file_manager.test() == False:
        log_manager.error("FileManager test failed. Please check your configuration and ensure the application has read/write access to the destination directory.")
        sys.exit(1)

    # check if user has a widevine or playready CDM, and do checks to see if they are valid.
    if config.app.skip_cdm_check is False:

        if MDNX_ENABLED:
            mdnx_widevine_valid = validate_cdm(MDNX_SERVICE_WIDEVINE_PATH, "Widevine", required=False)
            mdnx_playready_valid = validate_cdm(MDNX_SERVICE_PLAYREADY_PATH, "PlayReady", required=False)

            if mdnx_widevine_valid:
                log_manager.info("Widevine CDM is properly configured. multi-downloader-nx will utilize mp4decrypt with a widevine CDM for decryption.")

            if mdnx_playready_valid:
                log_manager.info("PlayReady CDM is properly configured. multi-downloader-nx will utilize mp4decrypt with a playready CDM for decryption.")

            if not mdnx_widevine_valid and not mdnx_playready_valid:
                log_manager.critical("No valid CDMs found for multi-downloader-nx. Downloading will not work without resolving this issue.\nPlease ensure you have either a Widevine or PlayReady CDM mounted to the correct path.")
                sys.exit(1)

    else:
        log_manager.warning("Skipping CDM checks because SKIP_CDM_CHECK is set to True. Make sure you have a valid Widevine or Playready CDM mounted to the correct path if you want downloading to work!")

    if ZLO_ENABLED:
        if not os.path.isfile(ZLO_SERVICE_BIN_PATH):
            log_manager.critical(f"ZLO is enabled, but the ZLO binary was not found at: {ZLO_SERVICE_BIN_PATH}\nPlease mount the correct ZLO binary and restart the application.")
            sys.exit(1)

        if not os.path.isdir(ZLO_SERVICE_CONFIG_SETTINGS_PATH):
            log_manager.critical(f"ZLO is enabled and the binary was found, but the settings folder was not found at: {ZLO_SERVICE_CONFIG_SETTINGS_PATH}\nPlease mount the correct ZLO settings folder and restart the application.")
            sys.exit(1)

        log_manager.info("ZLO checks completed. All good!")

    if PLEX_CONFIGURED is True or JELLY_CONFIGURED is True:
        if PLEX_CONFIGURED is True:
            log_manager.info("PLEX_URL is set. Plex media server scan enabled.")

        if JELLY_CONFIGURED is True:
            log_manager.info("JELLY_URL and JELLY_API_KEY are set. Jellyfin media server scan enabled.")

        if not mediaserver_auth():
            log_manager.error("Authentication timed out or failed. Check the logs.")
            sys.exit(1)

        log_manager.info("User is authenticated. Testing library scan...")
        if not mediaserver_scan_library():
            log_manager.error("Library scan failed. Please check your configuration.")
            sys.exit(1)
        else:
            log_manager.info("Library scan successful.")
    else:
        log_manager.info("No media servers configured. Skipping media server auth/scan.")

    match config.app.notification_preference:
        case "ntfy":
            log_manager.info("User prefers ntfy notifications. Setting up ntfy script...")

            script_path = config.app.ntfy_script_path

            if script_path is None or script_path == "":
                log_manager.error("NTFY_SCRIPT_PATH is not set or is empty. Please set it in config.json.")
                sys.exit(1)

            if not os.path.exists(script_path):
                log_manager.error(f"NTFY_SCRIPT_PATH does not exist: {script_path}. Please check the path in config.json.")
                sys.exit(1)

            from appdata.modules.NotificationManager import ntfy
            notifier = ntfy()

        case "smtp":
            log_manager.info("User prefers SMTP notifications. Configuring SMTP settings...")

            required_fields = [
                "smtp_from", "smtp_to", "smtp_host", "smtp_username",
                "smtp_password", "smtp_port", "smtp_starttls"
            ]

            missing_or_empty = []
            for field in required_fields:
                value = getattr(config.app, field)
                if value is None or value == "":
                    missing_or_empty.append(field)

            if missing_or_empty:
                log_manager.error(f"Missing or invalid SMTP configuration values: {', '.join(missing_or_empty)}")
                sys.exit(1)

            from appdata.modules.NotificationManager import SMTP
            notifier = SMTP()

        case "none":
            log_manager.info("User prefers no notifications.")
            notifier = None

        case _:
            log_manager.error(f"Unsupported notification preference: {config.app.notification_preference}. Supported options are 'ntfy', 'smtp' or 'none'.")
            sys.exit(1)

    for mdnx_service in SERVICES.mdnx.all():
        if not mdnx_service.enabled:
            log_manager.info(f"MDNX service '{mdnx_service.service_name}' is not enabled. Skipping...")
            continue

        match mdnx_service.service_name:
            case "crunchyroll":
                log_manager.info("Starting CR_MDNX_API...")
                from appdata.modules.API.MDNX.crunchy import CR_MDNX_API
                mdnx_service.api = CR_MDNX_API()

                # authenticate with MDNX crunchyroll service if needed or force auth if user wants to
                log_manager.info("Checking to see if user is authenticated with MDNX service (cr_token.yml exists?)...")
                if not os.path.exists(MDNX_SERVICE_CR_TOKEN_PATH) or config.app.cr_force_reauth == True:
                    log_manager.info("cr_token.yml not found or re-authentication forced. Starting authentication process...")
                    mdnx_service.api.auth()

                    # Update the "CR_FORCE_REAUTH" config to False if needed
                    if config.app.cr_force_reauth == True:
                        update_app_config("CR_FORCE_REAUTH", False)
                else:
                    log_manager.info("cr_token.yml exists. Assuming user is already authenticated with CR MDNX service.")

            case "hidive":
                log_manager.info("Starting HIDIVE_MDNX_API...")
                from appdata.modules.API.MDNX.hidive import HIDIVE_MDNX_API
                mdnx_service.api = HIDIVE_MDNX_API()

                # authenticate with MDNX hidive service if needed or force auth if user wants to
                log_manager.info("Checking to see if user is authenticated with MDNX service (hd_new_token.yml exists?)...")
                if not os.path.exists(MDNX_SERVICE_HIDIVE_TOKEN_PATH) or config.app.hidive_force_reauth == True:
                    log_manager.info("hd_new_token.yml not found or re-authentication forced. Starting authentication process...")
                    mdnx_service.api.auth()

                    # Update the "HIDIVE_FORCE_REAUTH" config to False if needed
                    if config.app.hidive_force_reauth == True:
                        update_app_config("HIDIVE_FORCE_REAUTH", False)
                else:
                    log_manager.info("hd_new_token.yml exists. Assuming user is already authenticated with HiDive MDNX service.")

            case "adn":
                log_manager.info("Starting ADN_MDNX_API...")
                from appdata.modules.API.MDNX.adn import ADN_MDNX_API
                mdnx_service.api = ADN_MDNX_API()

                # authenticate with MDNX adn service if needed or force auth if user wants to
                log_manager.info("Checking to see if user is authenticated with MDNX service (adn_token.yml exists?)...")
                if not os.path.exists(MDNX_SERVICE_ADN_TOKEN_PATH) or config.app.adn_force_reauth == True:
                    log_manager.info("adn_token.yml not found or re-authentication forced. Starting authentication process...")
                    mdnx_service.api.auth()

                    # Update the "ADN_FORCE_REAUTH" config to False if needed
                    if config.app.adn_force_reauth == True:
                        update_app_config("ADN_FORCE_REAUTH", False)
                else:
                    log_manager.info("adn_token.yml exists. Assuming user is already authenticated with ADN MDNX service.")

    for zlo_service in SERVICES.zlo.all():
        if not zlo_service.enabled:
            log_manager.info(f"ZLO service '{zlo_service.service_name}' is not enabled. Skipping...")
            continue

        match zlo_service.service_name:
            case "zlo-crunchyroll":
                log_manager.info("Starting CR_ZLO_API...")
                from appdata.modules.API.ZLO7.crunchy import CR_ZLO_API
                zlo_service.api = CR_ZLO_API()

            case "zlo-hidive":
                log_manager.info("Starting HIDIVE_ZLO_API...")
                from appdata.modules.API.ZLO7.hidive import HIDIVE_ZLO_API
                zlo_service.api = HIDIVE_ZLO_API()

            case "zlo-adn":
                log_manager.info("Starting ADN_ZLO_API...")
                from appdata.modules.API.ZLO7.adn import ADN_ZLO_API
                zlo_service.api = ADN_ZLO_API()

            case "zlo-disneyplus":
                log_manager.info("Starting DISNEY_ZLO_API...")
                from appdata.modules.API.ZLO7.disney import DISNEY_ZLO_API
                zlo_service.api = DISNEY_ZLO_API()

            case "zlo-amazon":
                log_manager.info("Starting AMAZON_ZLO_API...")
                from appdata.modules.API.ZLO7.amazon import AMAZON_ZLO_API
                zlo_service.api = AMAZON_ZLO_API()

    mainloop = MainLoop(notifier=notifier)

    def shutdown(signum, frame):
        """Signal handler to gracefully shutdown the application."""
        log_manager.info(f"Received signal {signum}. Start to shutdown...")
        mainloop.stop()
        log_manager.info("Shutdown requested. Waiting for MainLoop to exit...")

    # catch both Ctrl-C and Docker SIGTERM
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    mainloop.mainloop()


if __name__ == "__main__":
    log_manager.info("Overriding sys.excepthook to log uncaught exceptions...")
    sys.excepthook = handle_exception

    log_manager.info(f"mdnx-auto-dl v{APP_VERSION} has started.")
    get_running_user()
    update_mdnx_config()
    output_effective_config(config)
    validate_destinations()
    app()
