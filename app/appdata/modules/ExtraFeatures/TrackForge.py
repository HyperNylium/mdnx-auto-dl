import os
import subprocess

from appdata.modules.Globals import log_manager
from appdata.modules.Vars import config, BIN_DIR, get_season_monitor_config


TRACKFORGE_BIN_PATH = os.path.join(BIN_DIR, "trackforge", "trackforge")


def trackforge_resolve(service: str, series_id: str, season_id: str):
    """Work out the trackforge run for one episode. Returns (profile, workers, muxer) or None to skip."""

    service_config = config.extra_features.trackforge.services.get(service)
    if service_config is None or not service_config.enabled:
        return None

    # per-season trackforge profile overrides the service profile if set
    profile = service_config.profile
    season_monitor = get_season_monitor_config(service, series_id, season_id)
    if season_monitor is not None and season_monitor.trackforge_profile is not None:
        profile = season_monitor.trackforge_profile

    if profile.strip() == "":
        return None

    return profile, service_config.workers, service_config.muxer


def trackforge_run(path: str, profile: str, workers: int, muxer: str) -> bool:
    """Run trackforge on the file in place and return True on success. Blocks until done."""

    if not os.path.isfile(TRACKFORGE_BIN_PATH):
        log_manager.error(f"TrackForge binary not found at {TRACKFORGE_BIN_PATH}. Skipping TrackForge.")
        return False

    # keep input and output the same so trackforge overwrites the file in place. easier to handle for downstream processing
    cmd = [TRACKFORGE_BIN_PATH, path, path, profile, "--overwrite", "--simple", "--workers", str(workers), "--muxer", muxer]

    if str(config.app.log_level).lower() == "debug":
        cmd.append("-v")

    # stdout line-buffering if available
    if os.path.exists("/usr/bin/stdbuf"):
        cmd = ["stdbuf", "-oL", "-eL", *cmd]

    log_manager.info(f"Running TrackForge: {' '.join(cmd)}")

    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                log_manager.info(line.rstrip())

            returncode = proc.wait()
    except Exception as error:
        log_manager.error(f"Failed to run TrackForge: {error}", exc_info=error)
        return False

    if returncode != 0:
        log_manager.error(f"TrackForge failed with exit code {returncode}.")
        return False

    log_manager.info("TrackForge finished successfully.")
    return True
