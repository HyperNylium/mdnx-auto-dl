import os
import sys
import signal

# Custom imports
from appdata.modules.MDNX_API import MDNX_API
from appdata.modules.MainLoop import MainLoop
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

    # Start MainLoop
    logger.info("[app] Starting MainLoop...")
    mainloop = MainLoop(mdnx_api=mdnx_api)
    mainloop.start()

    def shutdown(signum, frame):
        logger.info(f"[app] Received signal {signum}. Start to shutdown...")

        # Stop MainLoop
        logger.info("[app] Stopping MainLoop...")
        mainloop.stop()

        logger.info("[app] MDNX-auto-dl has stopped cleanly. Exiting...")
        sys.exit(0)

    # catch both Ctrl-C and Docker SIGTERM
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

if __name__ == "__main__":
    logger.info("[app] Overriding sys.excepthook to log uncaught exceptions...")
    sys.excepthook = handle_exception

    logger.info("[app] MDNX-auto-dl has started.")
    get_running_user()
    update_mdnx_config()
    app()