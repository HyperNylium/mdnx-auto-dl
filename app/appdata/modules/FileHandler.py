import os
import time
from shutil import move as shmove

# Custom imports
from .Vars import logger, config



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

        logger.info(f"[FileHandler] FileHandler initialized.\nSource: {self.source}\nDestination: {self.dest}")

    def transfer(self, src_path: str, dst_path: str):
        name = os.path.basename(src_path)
        logger.info(f"[FileHandler] Starting transfer for {src_path}.")

        if not self.waitForReady(src_path):
            logger.warning(f"[FileHandler] {name} not ready within {self.readyTimeout} seconds, skipping.")
            return False

        parent_dir = os.path.dirname(dst_path)
        try:
            os.makedirs(parent_dir, exist_ok=True)
            logger.info(f"[FileHandler] Ensured directory exists: {parent_dir}")
        except Exception as e:
            logger.error(f"[FileHandler] Could not create directory {parent_dir}: {e}")
            return False

        if self.moveWithRetries(src_path, dst_path):
            logger.info(f"[FileHandler] Moved {name} to {dst_path}")
            return True
        else:
            logger.error(f"[FileHandler] Failed to move {name} after {self.moveRetries} attempts.")
            return False

    def remove_temp_files(self):
        for name in os.listdir(self.source):
            path = os.path.join(self.source, name)
            try:
                os.remove(path)
                logger.info(f"[FileHandler] Removed {path}")
            except Exception as e:
                logger.error(f"[FileHandler] Error removing {path}: {e}")

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

    def moveWithRetries(self, src, dst):
        for attempt in range(1, self.moveRetries + 1):
            try:
                shmove(src, dst)
                return True
            except Exception as e:
                logger.error(f"[FileHandler] (attempt {attempt} - Move failed for {src}: {e}")
                time.sleep(self.retryDelay)
        return False
