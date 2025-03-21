import os

# Import custom modules from appdata
from appdata.modules.MDNX_API import MDNX_API
from appdata.modules.Vars import logger, config
from appdata.modules.Vars import MDNX_SERVICE_BIN_PATH, MDNX_SERVICE_CR_TOKEN_PATH
from appdata.modules.Vars import check_dependencies, update_mdnx_config, update_app_config



def app():
    mdnx_api = MDNX_API(mdnx_path=MDNX_SERVICE_BIN_PATH)

    # Authenticate with MDNX service if needed or force auth if user wants to
    if not os.path.exists(MDNX_SERVICE_CR_TOKEN_PATH) or config["app"]["MDNX_API_FORCE_REAUTH"] == True:
        mdnx_api.auth()

        # update the "MDNX_API_FORCE_REAUTH" config to False
        if config["app"]["MDNX_API_FORCE_REAUTH"] == True:
            update_app_config("MDNX_API_FORCE_REAUTH", False)


    # Get the current queue
    queue_output = mdnx_api.queue_manager.output()
    if queue_output is not None:
        queue_ids = tuple(queue_output.keys())
    else:
        queue_ids = ()

    # Start monitoring series that are in the config file
    if len(config["monitor-series-id"]) != 0:
        for id in config["monitor-series-id"]:
            if id not in queue_ids:
                mdnx_api.start_monitor(id)
            else:
                logger.info(f"Series with ID: {id} is already being monitored.")

    # Stop monitoring series that are not in the config file
    if len(queue_ids) != 0:
        for id in queue_ids:
            if id not in config["monitor-series-id"]:
                mdnx_api.stop_monitor(id)


if __name__ == "__main__":
    logger.info("MDNX-auto-dl has started.")
    check_dependencies()
    update_mdnx_config()
    app()