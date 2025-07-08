import os
import time
from shutil import move as shmove

# Custom imports
from .Vars import logger, config



class FileHandler:
    def __init__(self):
        self.source = config["app"]["TEMP_DIR"]
        self.dest   = config["app"]["DATA_DIR"]
        self.readyCheckInterval = 1  # seconds between size checks
        self.readyStableSeconds = 5  # how long size must remain unchanged
        self.readyTimeout = 300      # overall timeout for readiness
        self.moveRetries = 3         # number of attempts to move file
        self.retryDelay = 5          # seconds between move attempts

        logger.info(f"[FileHandler] FileHandler initialized.\nSource: {self.source}\nDestination: {self.dest}")

    def transfer(self):
        for name in os.listdir(self.source):
            if not name.lower().endswith(".mkv"):
                continue
            srcPath = os.path.join(self.source, name)
            logger.info(f"[FileHandler] Starting transfer for {srcPath}.")

            if self.waitForReady(srcPath):
                dstPath = os.path.join(self.dest, name)
                if self.moveWithRetries(srcPath, dstPath):
                    logger.info(f"[FileHandler] Moved {name} to {self.dest}.")
                else:
                    logger.error(f"[FileHandler] Failed to move {name} after {self.moveRetries} attempts.")
            else:
                logger.warning(f"[FileHandler] {name} not ready within {self.readyTimeout} seconds, skipping.")

    def remove(self):
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
