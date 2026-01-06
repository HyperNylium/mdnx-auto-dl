import os
import sys
import signal

from appdata.modules.MainLoop import MainLoop
from appdata.modules.Globals import file_manager, log_manager
from appdata.modules.MediaServerManager import mediaserver_auth, mediaserver_scan_library
from appdata.modules.Vars import (
    config,
    CONFIG_DEFAULTS, MDNX_SERVICE_CR_TOKEN_PATH, MDNX_SERVICE_HIDIVE_TOKEN_PATH, PLEX_CONFIGURED, JELLY_CONFIGURED,
    update_mdnx_config, update_app_config, handle_exception, get_running_user, output_effective_config
)

__VERSION__ = "2.3.0"


def app():

    if file_manager.test() == False:
        log_manager.error("FileManager test failed. Please check your configuration and ensure the application has read/write access to the destination directory.")
        sys.exit(1)

    if config["app"]["CR_ENABLED"] == True:
        log_manager.info("Starting CR_MDNX_API...")
        from appdata.modules.API.MDNX.crunchy import CR_MDNX_API
        cr_mdnx_api = CR_MDNX_API()

        # authenticate with MDNX crunchyroll service if needed or force auth if user wants to
        log_manager.info("Checking to see if user is authenticated with MDNX service (cr_token.yml exists?)...")
        if not os.path.exists(MDNX_SERVICE_CR_TOKEN_PATH) or config["app"]["CR_FORCE_REAUTH"] == True:
            cr_mdnx_api.auth()

            # Update the "CR_FORCE_REAUTH" config to False if needed
            if config["app"]["CR_FORCE_REAUTH"] == True:
                update_app_config("CR_FORCE_REAUTH", False)
        else:
            log_manager.info("cr_token.yml exists. Assuming user is already authenticated with CR MDNX service.")

    if config["app"]["HIDIVE_ENABLED"] == True:
        log_manager.info("Starting HIDIVE_MDNX_API...")
        from appdata.modules.API.MDNX.hidive import HIDIVE_MDNX_API
        hidive_mdnx_api = HIDIVE_MDNX_API()

        # authenticate with MDNX hidive service if needed or force auth if user wants to
        log_manager.info("Checking to see if user is authenticated with MDNX service (hd_new_token.yml exists?)...")
        if not os.path.exists(MDNX_SERVICE_HIDIVE_TOKEN_PATH) or config["app"]["HIDIVE_FORCE_REAUTH"] == True:
            hidive_mdnx_api.auth()
            if config["app"]["HIDIVE_FORCE_REAUTH"] == True:
                update_app_config("HIDIVE_FORCE_REAUTH", False)
        else:
            log_manager.info("hd_new_token.yml exists. Assuming user is already authenticated with HiDive MDNX service.")

        if config["app"]["HIDIVE_SKIP_API_TEST"] == False:
            hidive_mdnx_api.test()
        else:
            log_manager.info("API test skipped by user.")

    # figure out notification preference
    log_manager.info("Checking notification preference...")
    if config["app"]["NOTIFICATION_PREFERENCE"] == "ntfy":
        log_manager.info("User prefers ntfy notifications. Setting up ntfy script...")

        script_path = config["app"]["NTFY_SCRIPT_PATH"]

        if script_path is None or script_path == "":
            log_manager.error("NTFY_SCRIPT_PATH is not set or is empty. Please set it in config.json.")
            sys.exit(1)

        if not os.path.exists(script_path):
            log_manager.error(f"NTFY_SCRIPT_PATH does not exist: {script_path}. Please check the path in config.json.")
            sys.exit(1)

        from appdata.modules.NotificationManager import ntfy
        notifier = ntfy()

    elif config["app"]["NOTIFICATION_PREFERENCE"] == "smtp":
        log_manager.info("User prefers SMTP notifications. Configuring SMTP settings...")

        required_keys = [
            "SMTP_FROM", "SMTP_TO", "SMTP_HOST", "SMTP_USERNAME",
            "SMTP_PASSWORD", "SMTP_PORT", "SMTP_STARTTLS"
        ]

        # ensure all keys exist AND are not None
        missing_or_empty = []
        for key in required_keys:
            value = config["app"][key]
            if value is None or value == "":
                missing_or_empty.append(key)

        if missing_or_empty:
            log_manager.error(f"Missing or invalid SMTP configuration values: {', '.join(missing_or_empty)}")
            sys.exit(1)

        from appdata.modules.NotificationManager import SMTP
        notifier = SMTP()

    elif config["app"]["NOTIFICATION_PREFERENCE"] == "none":
        log_manager.info("User prefers no notifications.")
        notifier = None

    else:
        log_manager.error(f"Unsupported notification preference: {config['app']['NOTIFICATION_PREFERENCE']}. Supported options are 'ntfy', 'smtp' or 'none'.")
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

    # init MainLoop based on enabled services
    if config["app"]["CR_ENABLED"] == True and config["app"]["HIDIVE_ENABLED"] == True:
        log_manager.info("Both CR and HIDIVE are enabled. Starting MainLoop with both services...")
        mainloop = MainLoop(cr_mdnx_api=cr_mdnx_api, hidive_mdnx_api=hidive_mdnx_api, notifier=notifier)

    elif config["app"]["CR_ENABLED"] == True and config["app"]["HIDIVE_ENABLED"] == False:
        log_manager.info("Only CR is enabled. Starting MainLoop with CR service only...")
        mainloop = MainLoop(cr_mdnx_api=cr_mdnx_api, hidive_mdnx_api=None, notifier=notifier)

    elif config["app"]["CR_ENABLED"] == False and config["app"]["HIDIVE_ENABLED"] == True:
        log_manager.info("Only HIDIVE is enabled. Starting MainLoop with HIDIVE service only...")
        mainloop = MainLoop(cr_mdnx_api=None, hidive_mdnx_api=hidive_mdnx_api, notifier=notifier)

    else:
        log_manager.error("Both CR_ENABLED and HIDIVE_ENABLED are set to False. Nothing to do. Exiting...")
        sys.exit(1)

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
    output_effective_config(config, CONFIG_DEFAULTS)
    app()
