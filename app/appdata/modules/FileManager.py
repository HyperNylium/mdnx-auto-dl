import os
import time
from shutil import copyfile as shcopy

from .Globals import log_manager
from .Vars import (
    config,
    TEMP_DIR, SERVICES,
    sanitize
)


class FileManager:
    def __init__(self):
        self.source = TEMP_DIR
        self.readyCheckInterval = 1  # seconds between size checks
        self.readyStableSeconds = 5  # how long size must remain unchanged
        self.readyTimeout = 300      # overall timeout for readiness
        self.moveRetries = 3         # number of attempts to move file
        self.retryDelay = 5          # seconds between move attempts

        # destinations get logged per-dir during test(), so keep this line minimal.
        log_manager.info(f"FileManager initialized with: Source: {self.source}")

    def test(self) -> bool:
        """Check that every enabled service's destination directory is accessible with read/write permissions."""

        dirs_to_test = []
        for service in SERVICES.all():
            if not service.enabled:
                continue

            dest_dir = config.destinations[service.service_name].dir
            if dest_dir not in dirs_to_test:
                dirs_to_test.append(dest_dir)

        for dest_dir in dirs_to_test:
            log_manager.info(f"Checking Read/Write permissions for: {dest_dir}")

            if not os.path.isdir(dest_dir):
                log_manager.error(f"Directory not found: {dest_dir}")
                return False

            # check read/write permissions
            can_r = os.access(dest_dir, os.R_OK)
            can_w = os.access(dest_dir, os.W_OK)
            log_manager.info(f"os.access -> R:{can_r} W:{can_w}")
            if not (can_r and can_w):
                log_manager.warning(f"Missing required R/W on {dest_dir}")
                return False

            # practical test for write/read permissions
            test_path = os.path.join(dest_dir, "permtest.txt")
            try:
                with open(test_path, "w", encoding="utf-8") as f:
                    f.write("ok")
                with open(test_path, "r", encoding="utf-8") as f:
                    data = f.read()
                success = (data == "ok")
                log_manager.info(f"Write/read test {'passed' if success else 'failed'} at {test_path}")
                if not success:
                    return False
            except Exception as e:
                log_manager.error(f"Write/read test failed in {dest_dir}: {e}")
                return False
            finally:
                try:
                    if os.path.exists(test_path):
                        os.remove(test_path)
                except Exception as e:
                    log_manager.warning(f"Could not clean up {test_path}\nMay fail when doing episode dub/sub updates\nFull error: {e}")

        return True

    def transfer(self, src_path: str, dst_path: str, overwrite: bool = False) -> bool:
        """Transfer a file from src_path to dst_path with readiness checks and retries."""

        log_manager.info(f"Starting transfer from '{src_path}' to '{dst_path}'")

        src_basename = os.path.basename(src_path)

        if not os.path.exists(src_path):
            log_manager.error(f"Downloaded file not found: {src_path}")
            return False

        log_manager.info(f"Found source file: {src_path}. Checking readiness...")

        if not self._wait_for_ready(src_path):
            log_manager.warning(f"'{src_basename}' not ready within {self.readyTimeout} seconds, skipping.")
            return False

        parts = dst_path.split(os.sep)
        sanitized = []
        for part in parts:
            if not part:
                continue
            sanitized.append(sanitize(part))

        log_manager.debug(f"Sanitized destination path parts: {sanitized}")

        if dst_path.startswith(os.sep):
            parent = os.sep + os.path.join(*sanitized[:-1])
        else:
            parent = os.path.join(*sanitized[:-1])
        final_dst = os.path.join(parent, sanitized[-1])

        log_manager.debug(f"Final destination path: {final_dst}")

        try:
            os.makedirs(parent, exist_ok=True)
            log_manager.debug(f"Ensured directory exists: {parent}")
        except Exception as e:
            log_manager.error(f"Could not create directory {parent}: {e}")
            return False

        if overwrite == True and os.path.exists(final_dst):
            try:
                os.remove(final_dst)
                log_manager.info(f"Removed existing file at destination: {final_dst}")
            except Exception as e:
                log_manager.error(f"Could not remove existing file {final_dst}: {e}")
                return False

        log_manager.info(f"Moving '{src_basename}' to '{final_dst}'")

        for attempt in range(1, self.moveRetries + 1):
            try:
                shcopy(src_path, final_dst)
                log_manager.info(f"Moved '{src_basename}' to '{final_dst}'")
                return True
            except Exception as e:
                log_manager.error(f"(attempt {attempt}) Move failed for '{src_basename}' to '{final_dst}': {e}")
                time.sleep(self.retryDelay)

        log_manager.error(f"Failed to move '{src_basename}' after {self.moveRetries} attempts.")
        return False

    def remove_temp_files(self):
        """Remove all files in the temporary source directory."""

        for name in os.listdir(self.source):
            path = os.path.join(self.source, name)
            log_manager.debug(f"removing {path}")
            try:
                os.remove(path)
                log_manager.debug(f"Removed {path}")
            except Exception as e:
                log_manager.error(f"Error removing {path}: {e}")

        log_manager.info(f"Temporary files in {self.source} removed.")
        return True

    def _wait_for_ready(self, path):
        """Wait for a file to become ready by monitoring its size stability over time."""

        lastSize = -1
        stableTime = 0
        start = time.time()

        while time.time() - start < self.readyTimeout:
            try:
                size = os.path.getsize(path)
            except Exception as e:
                log_manager.error(f"Error getting size for {path}: {e}")
                return False

            if size == lastSize:
                stableTime += self.readyCheckInterval
                log_manager.debug(f"Size unchanged for {stableTime} seconds (size={size} bytes)")
                if stableTime >= self.readyStableSeconds:
                    log_manager.debug(f"File '{path}' deemed ready after {stableTime} seconds of stability.")
                    return True
            else:
                log_manager.debug(f"Size changed: {lastSize} → {size} bytes")
                stableTime = 0
                lastSize = size

            time.sleep(self.readyCheckInterval)
        log_manager.warning(f"File '{path}' not ready within {self.readyTimeout} seconds timeout.")
        return False
