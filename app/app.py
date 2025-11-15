import os
import sys
import signal
import logging
import threading

# Custom imports
from appdata.modules.MainLoop import MainLoop
from appdata.modules.Globals import file_manager
from appdata.modules.MediaServerManager import mediaserver_auth, mediaserver_scan_library
from appdata.modules.Vars import (
    logger, config, CONFIG_DEFAULTS,
    MDNX_SERVICE_CR_TOKEN_PATH, MDNX_SERVICE_HIDIVE_TOKEN_PATH,
    update_mdnx_config, update_app_config, handle_exception, get_running_user, output_effective_config
)

__VERSION__ = "2.1.5"


def app():

    if file_manager.test() == False:
        logger.error("[app] FileManager test failed. Please check your configuration and ensure the application has read/write access to the destination directory.")
        sys.exit(1)

    if config["app"]["CR_ENABLED"] == True:
        logger.info("[app] Starting CR_MDNX_API...")
        from appdata.modules.CR_MDNX_API import CR_MDNX_API
        cr_mdnx_api = CR_MDNX_API()

        # Authenticate with CR MDNX service if needed or force auth if user wants to
        logger.info("[app] Checking to see if user is authenticated with MDNX service (cr_token.yml exists?)...")
        if not os.path.exists(MDNX_SERVICE_CR_TOKEN_PATH) or config["app"]["CR_FORCE_REAUTH"] == True:
            cr_mdnx_api.auth()

            # Update the "CR_FORCE_REAUTH" config to False if needed
            if config["app"]["CR_FORCE_REAUTH"] == True:
                update_app_config("CR_FORCE_REAUTH", False)
        else:
            logger.info("[app] cr_token.yml exists. Assuming user is already authenticated with CR MDNX service.")

    if config["app"]["HIDIVE_ENABLED"] == True:
        logger.info("[app] Starting HIDIVE_MDNX_API...")
        from appdata.modules.HIDIVE_MDNX_API import HIDIVE_MDNX_API
        hidive_mdnx_api = HIDIVE_MDNX_API()

        logger.info("[app] Checking to see if user is authenticated with MDNX service (hd_new_token.yml exists?)...")
        if not os.path.exists(MDNX_SERVICE_HIDIVE_TOKEN_PATH) or config["app"]["HIDIVE_FORCE_REAUTH"] == True:
            hidive_mdnx_api.auth()
            if config["app"]["HIDIVE_FORCE_REAUTH"] == True:
                update_app_config("HIDIVE_FORCE_REAUTH", False)
        else:
            logger.info("[app] hd_new_token.yml exists. Assuming user is already authenticated with HiDive MDNX service.")

        if config["app"]["HIDIVE_SKIP_API_TEST"] == False:
            hidive_mdnx_api.test()
        else:
            logger.info("[app] API test skipped by user.")

    # What is the notification preference?
    logger.info("[app] Checking notification preference...")
    if config["app"]["NOTIFICATION_PREFERENCE"] == "ntfy":
        logger.info("[app] User prefers ntfy notifications. Setting up ntfy script...")

        script_path = config["app"]["NTFY_SCRIPT_PATH"]

        if script_path is None or script_path == "":
            logger.error("[app] NTFY_SCRIPT_PATH is not set or is empty. Please set it in config.json.")
            sys.exit(1)

        if not os.path.exists(script_path):
            logger.error(f"[app] NTFY_SCRIPT_PATH does not exist: {script_path}. Please check the path in config.json.")
            sys.exit(1)

        from appdata.modules.NotificationManager import ntfy
        notifier = ntfy()

    elif config["app"]["NOTIFICATION_PREFERENCE"] == "smtp":
        logger.info("[app] User prefers SMTP notifications. Configuring SMTP settings...")

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
            logger.error(f"[app] Missing or invalid SMTP configuration values: {', '.join(missing_or_empty)}")
            sys.exit(1)

        from appdata.modules.NotificationManager import SMTP
        notifier = SMTP()

    elif config["app"]["NOTIFICATION_PREFERENCE"] == "none":
        logger.info("[app] User prefers no notifications.")
        notifier = None

    else:
        logger.error(f"[app] Unsupported notification preference: {config['app']['NOTIFICATION_PREFERENCE']}. Supported options are 'ntfy', 'smtp' or 'none'.")
        sys.exit(1)

    server_type = config["app"]["MEDIASERVER_TYPE"]

    if isinstance(server_type, str) and server_type.strip() != "":
        logger.debug(f"[app] Media server type: {server_type}")

        if not mediaserver_auth():
            logger.error("[app] Authentication timed out or failed. Check the logs.")
            sys.exit(1)

        logger.info("[app] User is authenticated. Testing library scan...")
        if not mediaserver_scan_library():
            logger.error("[app] Library scan failed. Please check your configuration.")
            sys.exit(1)
        else:
            logger.info("[app] Library scan successful.")
    else:
        logger.info("[app] MEDIASERVER_TYPE not set. Skipping media server auth/scan.")

    # Start MainLoop
    logger.info("[app] Starting MainLoop...")

    if config["app"]["CR_ENABLED"] == True and config["app"]["HIDIVE_ENABLED"] == True:
        logger.debug("[app] Both CR and HIDIVE are enabled. Starting MainLoop with both services...")
        mainloop = MainLoop(cr_mdnx_api=cr_mdnx_api, hidive_mdnx_api=hidive_mdnx_api, notifier=notifier)

    elif config["app"]["CR_ENABLED"] == True and config["app"]["HIDIVE_ENABLED"] == False:
        logger.debug("[app] Only CR is enabled. Starting MainLoop with CR service only...")
        mainloop = MainLoop(cr_mdnx_api=cr_mdnx_api, hidive_mdnx_api=None, notifier=notifier)

    elif config["app"]["CR_ENABLED"] == False and config["app"]["HIDIVE_ENABLED"] == True:
        logger.debug("[app] Only HIDIVE is enabled. Starting MainLoop with HIDIVE service only...")
        mainloop = MainLoop(cr_mdnx_api=None, hidive_mdnx_api=hidive_mdnx_api, notifier=notifier)

    else:
        logger.error("[app] Both CR_ENABLED and HIDIVE_ENABLED are set to False. Nothing to do. Exiting...")
        sys.exit(1)

    mainloop.start()

    # capture uncaught exceptions from threads (Py 3.8+), so we can exit non-zero
    exit_code = {"code": 0}
    if hasattr(threading, "excepthook"):
        def _thread_excepthook(args):
            # Treat SystemExit as intentional shutdown.
            if issubclass(args.exc_type, SystemExit):
                code = getattr(args.exc_value, "code", 1)
                try:
                    exit_code["code"] = int(code)
                except Exception:
                    exit_code["code"] = 1
                return

            # Real crash: log it and force non-zero
            logger.error(f"[app] Uncaught exception in thread {args.thread.name}",
                        exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
            exit_code["code"] = 1
        threading.excepthook = _thread_excepthook
    else:
        logger.warning("[app] threading.excepthook unavailable. Worker crash exit codes may not propagate.")

    def shutdown(signum, frame):
        logger.info(f"[app] Received signal {signum}. Start to shutdown...")
        mainloop.stop()
        logger.info("[app] mdnx-auto-dl has stopped cleanly. Exiting...")

    # catch both Ctrl-C and Docker SIGTERM
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # block main thread until the worker ends (normal or crash)
    mainloop.thread.join()
    logging.shutdown()
    sys.exit(exit_code["code"])


if __name__ == "__main__":
    logger.info("[app] Overriding sys.excepthook to log uncaught exceptions...")
    sys.excepthook = handle_exception

    logger.info(f"[app] mdnx-auto-dl v{__VERSION__} has started.")
    get_running_user()
    update_mdnx_config()
    output_effective_config(config, CONFIG_DEFAULTS)
    app()
