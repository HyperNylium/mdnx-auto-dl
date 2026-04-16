import os
import sys
import signal

from appdata.modules.MainLoop import MainLoop
from appdata.modules.Globals import file_manager, log_manager
from appdata.modules.MediaServerManager import mediaserver_auth, mediaserver_scan_library
from appdata.modules.Vars import (
    config,
    MDNX_SERVICE_CR_TOKEN_PATH, MDNX_SERVICE_HIDIVE_TOKEN_PATH, MDNX_SERVICE_WIDEVINE_PATH, MDNX_SERVICE_PLAYREADY_PATH,
    ZLO_SERVICE_BIN_PATH, ZLO_SERVICE_CONFIG_SETTINGS_PATH, ZLO_SERVICE_WIDEVINE_L1_PATH, ZLO_SERVICE_WIDEVINE_L3_PATH, ZLO_SERVICE_PLAYREADY_SL2K_PATH, ZLO_SERVICE_PLAYREADY_SL3K_PATH,
    MDNX_ENABLED, ZLO_ENABLED, PLEX_CONFIGURED, JELLY_CONFIGURED,
    validate_cdm, update_mdnx_config, update_app_config, handle_exception, get_running_user, output_effective_config
)

__VERSION__ = "3.0.0"


def app():

    # can we reliably read/write to the destination directory?
    if file_manager.test() == False:
        log_manager.error("FileManager test failed. Please check your configuration and ensure the application has read/write access to the destination directory.")
        sys.exit(1)

    # check if user has a widevine or playready CDM, and do checks to see if they are valid.
    if config.app.skip_cdm_check is False:

        # MDNX checks
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

        # ZLO checks
        if ZLO_ENABLED:
            if not os.path.isfile(ZLO_SERVICE_BIN_PATH):
                log_manager.critical(f"ZLO is enabled, but the ZLO binary was not found at: {ZLO_SERVICE_BIN_PATH}")
                sys.exit(1)

            if not os.path.isdir(ZLO_SERVICE_CONFIG_SETTINGS_PATH):
                log_manager.critical(f"ZLO is enabled, but the settings folder was not found at: {ZLO_SERVICE_CONFIG_SETTINGS_PATH}\nPlease mount the correct ZLO settings folder.")
                sys.exit(1)

            zlo_widevine_l1_valid = validate_cdm(ZLO_SERVICE_WIDEVINE_L1_PATH, "Widevine", required=True)
            if zlo_widevine_l1_valid:
                log_manager.info("Widevine L1 CDM is properly configured for ZLO.")

            zlo_widevine_l3_valid = validate_cdm(ZLO_SERVICE_WIDEVINE_L3_PATH, "Widevine", required=True)
            if zlo_widevine_l3_valid:
                log_manager.info("Widevine L3 CDM is properly configured for ZLO.")

            zlo_playready_sl2k_valid = validate_cdm(ZLO_SERVICE_PLAYREADY_SL2K_PATH, "PlayReady", required=True)
            if zlo_playready_sl2k_valid:
                log_manager.info("PlayReady SL2K CDM is properly configured for ZLO.")

            sl3k_device_paths = []
            if os.path.isdir(ZLO_SERVICE_PLAYREADY_SL3K_PATH):
                for name in os.listdir(ZLO_SERVICE_PLAYREADY_SL3K_PATH):
                    full_path = os.path.join(ZLO_SERVICE_PLAYREADY_SL3K_PATH, name)
                    if os.path.isdir(full_path):
                        sl3k_device_paths.append((name, full_path))

            if not sl3k_device_paths:
                log_manager.critical(f"ZLO is enabled, but no PlayReady SL3K device folders were found at: {ZLO_SERVICE_PLAYREADY_SL3K_PATH}")
                sys.exit(1)

            for device_name, device_path in sl3k_device_paths:
                sl3k_valid = validate_cdm(device_path, "PlayReady", required=True)
                if sl3k_valid:
                    log_manager.info(f"PlayReady SL3K CDM is properly configured for ZLO device folder: {device_name}")

            log_manager.info("ZLO CDM checks completed. ZLO will utilize either mp4decrypt or shaka packager with the appropriate CDMs for decryption.")

        if not MDNX_ENABLED and not ZLO_ENABLED:
            log_manager.warning("CDM checks are enabled but no services that require CDMs are enabled. Exiting...")
            sys.exit(0)

    else:
        log_manager.warning("Skipping CDM checks because SKIP_CDM_CHECK is set to True. Make sure you have a valid Widevine or Playready CDM mounted to the correct path if you want downloading to work!")

    # authenticate with media server(s) if configured
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

    # figure out notification preference
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

    # service checks/auth
    cr_mdnx_api = None
    if config.app.cr_enabled == True:
        log_manager.info("Starting CR_MDNX_API...")
        from appdata.modules.API.MDNX.crunchy import CR_MDNX_API
        cr_mdnx_api = CR_MDNX_API()

        # authenticate with MDNX crunchyroll service if needed or force auth if user wants to
        log_manager.info("Checking to see if user is authenticated with MDNX service (cr_token.yml exists?)...")
        if not os.path.exists(MDNX_SERVICE_CR_TOKEN_PATH) or config.app.cr_force_reauth == True:
            log_manager.info("cr_token.yml not found or re-authentication forced. Starting authentication process...")
            cr_mdnx_api.auth()

            # Update the "CR_FORCE_REAUTH" config to False if needed
            if config.app.cr_force_reauth == True:
                update_app_config("CR_FORCE_REAUTH", False)
        else:
            log_manager.info("cr_token.yml exists. Assuming user is already authenticated with CR MDNX service.")

    hidive_mdnx_api = None
    if config.app.hidive_enabled == True:
        log_manager.info("Starting HIDIVE_MDNX_API...")
        from appdata.modules.API.MDNX.hidive import HIDIVE_MDNX_API
        hidive_mdnx_api = HIDIVE_MDNX_API()

        # authenticate with MDNX hidive service if needed or force auth if user wants to
        log_manager.info("Checking to see if user is authenticated with MDNX service (hd_new_token.yml exists?)...")
        if not os.path.exists(MDNX_SERVICE_HIDIVE_TOKEN_PATH) or config.app.hidive_force_reauth == True:
            log_manager.info("hd_new_token.yml not found or re-authentication forced. Starting authentication process...")
            hidive_mdnx_api.auth()

            # Update the "HIDIVE_FORCE_REAUTH" config to False if needed
            if config.app.hidive_force_reauth == True:
                update_app_config("HIDIVE_FORCE_REAUTH", False)
        else:
            log_manager.info("hd_new_token.yml exists. Assuming user is already authenticated with HiDive MDNX service.")

    zlo_cr_api = None
    if config.app.zlo_cr_enabled is True:
        log_manager.info("Starting CR_ZLO_API...")
        from appdata.modules.API.ZLO7.crunchy import CR_ZLO_API
        zlo_cr_api = CR_ZLO_API()

    zlo_hidive_api = None
    if config.app.zlo_hidive_enabled is True:
        log_manager.info("Starting HIDIVE_ZLO_API...")
        from appdata.modules.API.ZLO7.hidive import HIDIVE_ZLO_API
        zlo_hidive_api = HIDIVE_ZLO_API()

    zlo_adn_api = None
    if config.app.zlo_adn_enabled is True:
        log_manager.info("Starting ADN_ZLO_API...")
        from appdata.modules.API.ZLO7.adn import ADN_ZLO_API
        zlo_adn_api = ADN_ZLO_API()

    mainloop = MainLoop(
        cr_mdnx_api=cr_mdnx_api,
        hidive_mdnx_api=hidive_mdnx_api,
        zlo_cr_api=zlo_cr_api,
        zlo_hidive_api=zlo_hidive_api,
        zlo_adn_api=zlo_adn_api,
        notifier=notifier
    )

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

    log_manager.info(f"mdnx-auto-dl v{__VERSION__} has started.")
    get_running_user()
    update_mdnx_config()
    output_effective_config(config)
    app()
