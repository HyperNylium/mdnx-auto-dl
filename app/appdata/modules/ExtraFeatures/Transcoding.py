import os
import shlex
import subprocess

from appdata.modules.Globals import log_manager
from appdata.modules.Vars import config, get_season_monitor_config


def transcode_resolve(service: str, series_id: str, season_id: str):
    """Work out the ffmpeg command for one episode. Returns the command string or None to skip."""

    service_features = config.extra_features.services.get(service)
    if service_features is None or not service_features.transcoding.enabled:
        return None

    service_config = service_features.transcoding

    # per-season command overrides the service command if set
    command = service_config.ffmpeg_command
    season_monitor = get_season_monitor_config(service, series_id, season_id)
    if season_monitor is not None and season_monitor.ffmpeg_command is not None:
        command = season_monitor.ffmpeg_command

    if command.strip() == "":
        return None

    return command


def transcode_run(path: str, ffmpeg_command: str) -> bool:
    """Run the ffmpeg command on the file and swap the result in. Blocks until done."""

    # ffmpeg can not read and write the same file so we write to a temp output file first
    root, extension = os.path.splitext(path)
    output_path = f"{root}.transcoded{extension}"

    if os.path.exists(output_path):
        os.remove(output_path)

    cmd = []
    for token in shlex.split(ffmpeg_command):
        cmd.append(token.replace("{input}", path).replace("{output}", output_path))

    # stdout line-buffering if available
    if os.path.exists("/usr/bin/stdbuf"):
        cmd = ["stdbuf", "-oL", "-eL", *cmd]

    log_manager.info(f"Running transcode: {' '.join(cmd)}")

    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                log_manager.info(line.rstrip())

            returncode = proc.wait()
    except Exception as error:
        log_manager.error(f"Failed to run transcode: {error}", exc_info=error)
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

    if returncode != 0:
        log_manager.error(f"Transcode failed with exit code {returncode}.")
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

    # swap the transcoded file in for the original so the transfer step uses the processed file
    try:
        os.replace(output_path, path)
    except Exception as error:
        log_manager.error(f"Failed to move transcoded file into place: {error}", exc_info=error)
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

    log_manager.info("Transcode finished successfully.")
    return True
