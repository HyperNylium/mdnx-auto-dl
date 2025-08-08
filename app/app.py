import os
import sys
import signal
import threading

# Custom imports
from appdata.modules.MDNX_API import MDNX_API
from appdata.modules.MainLoop import MainLoop
from appdata.modules.NotificationManager import ntfy, SMTP
from appdata.modules.Vars import logger, config
from appdata.modules.Vars import MDNX_SERVICE_BIN_PATH, MDNX_SERVICE_CR_TOKEN_PATH
from appdata.modules.Vars import update_mdnx_config, update_app_config, handle_exception, get_running_user



def app():
    logger.info("[app] Initializing MDNX API...")
    mdnx_api = MDNX_API(mdnx_path=MDNX_SERVICE_BIN_PATH)
    logger.info("[app] MDNX API initialized.")

    # Authenticate with MDNX service if needed or force auth if user wants to
    logger.info("[app] Checking to see if user is authenticated with MDNX service (cr_token.yml exists?)...")
    if not os.path.exists(MDNX_SERVICE_CR_TOKEN_PATH) or config["app"]["CR_FORCE_REAUTH"] == True:
        mdnx_api.auth()

        # Update the "CR_FORCE_REAUTH" config to False if needed
        logger.info("[app] Checking to see if user wants to force re-auth with MDNX service...")
        if config["app"]["CR_FORCE_REAUTH"] == True:
            update_app_config("CR_FORCE_REAUTH", False)
        else:
            logger.info("[app] User does not want to force re-auth with MDNX service.")
    else:
        logger.info("[app] cr_token.yml exists. Assuming user is already authenticated with MDNX service.")

    # What is the notification preference?
    logger.info("[app] Checking notification preference...")
    if config["app"]["NOTIFICATION_PREFERENCE"] == "ntfy":
        logger.info("[app] User prefers ntfy notifications. Setting up ntfy script...")
        if not os.path.exists(config["app"]["NTFY_SCRIPT_PATH"]):
            logger.error(f"[app] Ntfy script not found at {config['app']['NTFY_SCRIPT_PATH']}. Please check your configuration.")
            sys.exit(1)
        notifier = ntfy()
    elif config["app"]["NOTIFICATION_PREFERENCE"] == "smtp":
        logger.info("[app] User prefers SMTP notifications. Configuring SMTP settings...")
        if not all(key in config["app"] for key in ["SMTP_FROM", "SMTP_TO", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_PORT", "SMTP_STARTTLS"]):
            logger.error("[app] Missing SMTP configuration parameters. Please check your configuration.")
            sys.exit(1)
        notifier = SMTP()
    elif config["app"]["NOTIFICATION_PREFERENCE"] == "none":
        logger.info("[app] User prefers no notifications.")
        notifier = None
    else:
        logger.error(f"[app] Unsupported notification preference: {config['app']['NOTIFICATION_PREFERENCE']}. Supported options are 'ntfy', 'smtp' or 'none'.")
        sys.exit(1)

    # Start MainLoop
    logger.info("[app] Starting MainLoop...")
    mainloop = MainLoop(mdnx_api=mdnx_api, notifier=notifier)
    mainloop.start()

    MainLoopEvent = threading.Event()

    def shutdown(signum, frame):
        logger.info(f"[app] Received signal {signum}. Start to shutdown...")
        mainloop.stop()
        logger.info("[app] mdnx-auto-dl has stopped cleanly. Exiting...")
        MainLoopEvent.set()

    # catch both Ctrl-C and Docker SIGTERM
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # park the main thread until shutdown is requested
    MainLoopEvent.wait()

if __name__ == "__main__":
    logger.info("[app] Overriding sys.excepthook to log uncaught exceptions...")
    sys.excepthook = handle_exception

    logger.info("[app] mdnx-auto-dl has started.")
    get_running_user()
    update_mdnx_config()
    app()