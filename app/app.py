import os
import sys
import signal

from appdata.modules.MainLoop import MainLoop
from appdata.modules.Globals import file_manager, log_manager
from appdata.modules.MediaServerManager import mediaserver_auth, mediaserver_scan_library
from appdata.modules.Vars import (
    config,
    MDNX_SERVICE_CR_TOKEN_PATH, MDNX_SERVICE_HIDIVE_TOKEN_PATH, MDNX_SERVICE_WIDEVINE_PATH, MDNX_SERVICE_PLAYREADY_PATH,
    MDNX_CR_ENABLED, MDNX_HIDIVE_ENABLED, PLEX_CONFIGURED, JELLY_CONFIGURED,
    update_mdnx_config, update_app_config, handle_exception, get_running_user, output_effective_config
)

__VERSION__ = "2.3.2"


def app():

    # can we reliably read/write to the destination directory?
    if file_manager.test() == False:
        log_manager.error("FileManager test failed. Please check your configuration and ensure the application has read/write access to the destination directory.")
        sys.exit(1)

    # check if user has a widevine or playready CDM, and do checks to see if they are valid.
    widevine_cdm_found = False
    playready_cdm_found = False
    services = [
        (MDNX_SERVICE_WIDEVINE_PATH, "Widevine"),
        (MDNX_SERVICE_PLAYREADY_PATH, "PlayReady")
    ]

    for service_path, service_name in services:
        service_folder_contents = os.listdir(service_path)

        log_manager.debug(f"Checking {service_name} CDM path at: {service_path}.\nContents: {service_folder_contents}")

        # folder exists, but may have no files (user not using this CDM)
        # if no files, skip checks
        has_files = False
        for name in service_folder_contents:
            if name == ".gitkeep":
                continue

            full = os.path.join(service_path, name)
            if os.path.isfile(full):
                has_files = True
                break

        if not has_files:
            log_manager.debug(f"{service_name} CDM path is empty (no files). Skipping {service_name} checks.")
            continue

        match service_name:
            case "Widevine":
                log_manager.info(f"Checking Widevine CDM at {service_path}...")

                found_file = False
                found_blobs = {
                    ".bin": False,
                    ".pem": False
                }

                for name in service_folder_contents:
                    full = os.path.join(service_path, name)
                    if not os.path.isfile(full):
                        continue

                    lower = name.lower()

                    if lower.endswith(".wvd"):
                        found_file = True
                        break

                    for ext in found_blobs:
                        if lower.endswith(ext):
                            found_blobs[ext] = True

                if found_file:
                    log_manager.info("Widevine CDM file (.wvd) found. Good to go!")
                    widevine_cdm_found = True
                    break
                elif all(found_blobs.values()):
                    log_manager.info("Widevine CDM blob files (.bin and .pem) found. Good to go!")
                    widevine_cdm_found = True
                    break
                else:
                    log_manager.critical(
                        "Widevine CDM not properly configured. Downloading will not work without resolving this issue.\n"
                        "Please ensure you have either the .wvd file or both .bin and .pem blob files mounted to the correct path.\n"
                        "Should be as simple as uncommenting the '# Widevine' section in your docker-compose.yaml and putting the files in the right place.\n"
                        "If you need more help, feel free to open a discussion on the GitHub repo :)"
                    )
                    sys.exit(1)

            case "PlayReady":
                log_manager.info(f"Checking PlayReady CDM at {service_path}...")

                found_file = False
                found_blobs = {
                    "bgroupcert.dat": False,
                    "zgpriv.dat": False
                }

                for name in service_folder_contents:
                    full = os.path.join(service_path, name)
                    if not os.path.isfile(full):
                        continue

                    lower = name.lower()

                    if lower.endswith(".prd"):
                        found_file = True
                        break

                    for blob_name in found_blobs:
                        if lower == blob_name.lower():
                            found_blobs[blob_name] = True

                if found_file:
                    log_manager.info("Playready CDM file (.prd) found. Good to go!")
                    playready_cdm_found = True
                    break
                elif all(found_blobs.values()):
                    log_manager.info("Playready CDM blob files (bgroupcert.dat and zgpriv.dat) found. Checking to see if they are valid...")

                    # check that bgroupcert.dat is at least 1KB, and zgpriv.dat is exactly 32 bytes.
                    # these stats are from multi-downloader-nx's docs.
                    bgroupcert_path = os.path.join(service_path, "bgroupcert.dat")
                    zgpriv_path = os.path.join(service_path, "zgpriv.dat")

                    bgroupcert_size = os.path.getsize(bgroupcert_path)
                    zgpriv_size = os.path.getsize(zgpriv_path)

                    if bgroupcert_size >= 1024 and zgpriv_size == 32:
                        log_manager.info("Playready CDM blob files look valid. Good to go!")
                        playready_cdm_found = True
                        break
                    else:
                        log_manager.critical(
                            "Playready CDM blob files found but look invalid:\n"
                            f"- bgroupcert.dat size: {bgroupcert_size} bytes (should be at least 1024 bytes)\n"
                            f"- zgpriv.dat size: {zgpriv_size} bytes (should be exactly 32 bytes)\n"
                            "Please check your mounted files."
                        )
                        sys.exit(1)

                else:
                    log_manager.critical(
                        "Playready CDM not properly configured. Downloading will not work without resolving this issue.\n"
                        "Please ensure you have either the .prd file or both bgroupcert.dat and zgpriv.dat blob files mounted to the correct path.\n"
                        "Should be as simple as uncommenting the '# Playready' section in your docker-compose.yaml and putting the files in the right place.\n"
                        "If you need more help, feel free to open a discussion on the GitHub repo :)"
                    )
                    sys.exit(1)

    if widevine_cdm_found:
        log_manager.info("Widevine CDM is properly configured. multi-downloader-nx will utilize mp4decrypt with a widevine CDM for decryption.")

    if playready_cdm_found:
        log_manager.info("Playready CDM is properly configured. multi-downloader-nx will utilize mp4decrypt with a playready CDM for decryption.")

    if not widevine_cdm_found and not playready_cdm_found:
        log_manager.critical(
            "No valid CDMs found. Downloading will not work without resolving this issue.\n"
            "Please ensure you have either a Widevine or Playready CDM mounted to the correct path.\n"
            "Should be as simple as uncommenting the relevant section in your docker-compose.yaml and putting the files in the right place.\n"
            "If you need more help, feel free to open a discussion on the GitHub repo :)"
        )
        sys.exit(1)

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
    if MDNX_CR_ENABLED == True:
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
    if MDNX_HIDIVE_ENABLED == True:
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

    mainloop = MainLoop(cr_mdnx_api=cr_mdnx_api, hidive_mdnx_api=hidive_mdnx_api, notifier=notifier)

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
