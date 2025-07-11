import os
import time
from shutil import move as shmove

# Custom imports
from .Vars import logger, config
from .Vars import sanitize

class FileHandler:
    def __init__(self):
        self.source = config["app"]["TEMP_DIR"]
        self.dest   = config["app"]["DATA_DIR"]
        # These should be configurable from config.json in the future.
        self.readyCheckInterval = 1  # seconds between size checks
        self.readyStableSeconds = 5  # how long size must remain unchanged
        self.readyTimeout = 300      # overall timeout for readiness
        self.moveRetries = 3         # number of attempts to move file
        self.retryDelay = 5          # seconds between move attempts

        logger.info(f"[FileHandler] FileHandler initialized with: Source: {self.source} | Destination: {self.dest}")

    def transfer(self, src_path: str, dst_path: str) -> bool:
        logger.info(f"[FileHandler] Starting transfer from '{src_path}' to '{dst_path}'")

        src_basename = os.path.basename(src_path)

        if not os.path.exists(src_path):
            logger.error(f"[FileHandler] Downloaded file not found: {src_path}")
            return False
        logger.info(f"[FileHandler] Downloaded source: {src_path}")

        if not self.waitForReady(src_path):
            logger.warning(f"[FileHandler] '{src_basename}' not ready within {self.readyTimeout} seconds, skipping.")
            return False

        parts = dst_path.split(os.sep)
        sanitized = []
        for part in parts:
            if not part:
                continue
            sanitized.append(sanitize(part))

        if dst_path.startswith(os.sep):
            parent = os.sep + os.path.join(*sanitized[:-1])
        else:
            parent = os.path.join(*sanitized[:-1])
        final_dst = os.path.join(parent, sanitized[-1])

        try:
            os.makedirs(parent, exist_ok=True)
            logger.info(f"[FileHandler] Ensured directory exists: {parent}")
        except Exception as e:
            logger.error(f"[FileHandler] Could not create directory {parent}: {e}")
            return False

        for attempt in range(1, self.moveRetries + 1):
            try:
                shmove(src_path, final_dst)
                logger.info(f"[FileHandler] Moved '{src_basename}' to '{final_dst}'")
                return True
            except Exception as e:
                logger.error(f"[FileHandler] (attempt {attempt}) Move failed for '{src_basename}' to '{final_dst}': {e}")
                time.sleep(self.retryDelay)

        logger.error(f"[FileHandler] Failed to move '{src_basename}' after {self.moveRetries} attempts.")
        return False

    def waitForReady(self, path):
        lastSize = -1
        stableTime = 0
        start = time.time()

        while time.time() - start < self.readyTimeout:
            try:
                size = os.path.getsize(path)
            except Exception as e:
                logger.error(f"[FileHandler] Error getting size for {path}: {e}")
                return False

            if size == lastSize:
                stableTime += self.readyCheckInterval
                if stableTime >= self.readyStableSeconds:
                    return True
            else:
                stableTime = 0
                lastSize = size

            time.sleep(self.readyCheckInterval)
        return False

    def remove_temp_files(self):
        for name in os.listdir(self.source):
            path = os.path.join(self.source, name)
            try:
                os.remove(path)
                logger.info(f"[FileHandler] Removed {path}")
            except Exception as e:
                logger.error(f"[FileHandler] Error removing {path}: {e}")
