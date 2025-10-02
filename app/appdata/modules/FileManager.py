import os
import time
from shutil import copyfile as shcopy

# Custom imports
from .Vars import (
    logger,
    TEMP_DIR, DATA_DIR,
    sanitize
)



class FileManager:
    def __init__(self):
        self.source = TEMP_DIR
        self.dest = DATA_DIR
        self.readyCheckInterval = 1  # seconds between size checks
        self.readyStableSeconds = 5  # how long size must remain unchanged
        self.readyTimeout = 300      # overall timeout for readiness
        self.moveRetries = 3         # number of attempts to move file
        self.retryDelay = 5          # seconds between move attempts

        logger.info(f"[FileManager] FileManager initialized with: Source: {self.source} | Destination: {self.dest}")

    def test(self) -> bool:
        logger.info(f"[FileManager] Checking Read/Write permissions for: {self.dest}")

        if not os.path.isdir(self.dest):
            logger.error(f"[FileManager] Directory not found: {self.dest}")
            return False

        can_r = os.access(self.dest, os.R_OK)
        can_w = os.access(self.dest, os.W_OK)
        logger.info(f"[FileManager] os.access -> R:{can_r} W:{can_w}")
        if not (can_r and can_w):
            logger.warning(f"[FileManager] Missing required R/W on {self.dest}")
            return False

        test_path = os.path.join(self.dest, "permtest.txt")
        try:
            with open(test_path, "w", encoding="utf-8") as f:
                f.write("ok")
            with open(test_path, "r", encoding="utf-8") as f:
                data = f.read()
            success = (data == "ok")
            logger.info(f"[FileManager] Write/read test {'passed' if success else 'failed'} at {test_path}")
            return success
        except Exception as e:
            logger.error(f"[FileManager] Write/read test failed in {self.dest}: {e}")
            return False
        finally:
            try:
                if os.path.exists(test_path):
                    os.remove(test_path)
            except Exception as e:
                logger.warning(f"[FileManager] Could not clean up {test_path}\nMay fail when doing episode dub/sub updates\nFull error: {e}")

    def transfer(self, src_path: str, dst_path: str, overwrite: bool = False) -> bool:
        logger.info(f"[FileManager] Starting transfer from '{src_path}' to '{dst_path}'")

        src_basename = os.path.basename(src_path)

        if not os.path.exists(src_path):
            logger.error(f"[FileManager] Downloaded file not found: {src_path}")
            return False

        logger.info(f"[FileManager] Found source file: {src_path}. Checking readiness...")

        if not self.waitForReady(src_path):
            logger.warning(f"[FileManager] '{src_basename}' not ready within {self.readyTimeout} seconds, skipping.")
            return False

        parts = dst_path.split(os.sep)
        sanitized = []
        for part in parts:
            if not part:
                continue
            sanitized.append(sanitize(part))

        logger.debug(f"[FileManager] Sanitized destination path parts: {sanitized}")

        if dst_path.startswith(os.sep):
            parent = os.sep + os.path.join(*sanitized[:-1])
        else:
            parent = os.path.join(*sanitized[:-1])
        final_dst = os.path.join(parent, sanitized[-1])

        logger.debug(f"[FileManager] Final destination path: {final_dst}")

        try:
            os.makedirs(parent, exist_ok=True)
            logger.debug(f"[FileManager] Ensured directory exists: {parent}")
        except Exception as e:
            logger.error(f"[FileManager] Could not create directory {parent}: {e}")
            return False

        if overwrite == True and os.path.exists(final_dst):
            try:
                os.remove(final_dst)
                logger.info(f"[FileManager] Removed existing file at destination: {final_dst}")
            except Exception as e:
                logger.error(f"[FileManager] Could not remove existing file {final_dst}: {e}")
                return False

        logger.info(f"[FileManager] Moving '{src_basename}' to '{final_dst}'")

        for attempt in range(1, self.moveRetries + 1):
            try:
                shcopy(src_path, final_dst)
                logger.info(f"[FileManager] Moved '{src_basename}' to '{final_dst}'")
                return True
            except Exception as e:
                logger.error(f"[FileManager] (attempt {attempt}) Move failed for '{src_basename}' to '{final_dst}': {e}")
                time.sleep(self.retryDelay)

        logger.error(f"[FileManager] Failed to move '{src_basename}' after {self.moveRetries} attempts.")
        return False

    def waitForReady(self, path):
        lastSize = -1
        stableTime = 0
        start = time.time()

        while time.time() - start < self.readyTimeout:
            try:
                size = os.path.getsize(path)
            except Exception as e:
                logger.error(f"[FileManager] Error getting size for {path}: {e}")
                return False

            if size == lastSize:
                stableTime += self.readyCheckInterval
                logger.debug(f"[FileManager] Size unchanged for {stableTime} seconds (size={size} bytes)")
                if stableTime >= self.readyStableSeconds:
                    logger.debug(f"[FileManager] File '{path}' deemed ready after {stableTime} seconds of stability.")
                    return True
            else:
                logger.debug(f"[FileManager] Size changed: {lastSize} → {size} bytes")
                stableTime = 0
                lastSize = size

            time.sleep(self.readyCheckInterval)
        logger.warning(f"[FileManager] File '{path}' not ready within {self.readyTimeout} seconds timeout.")
        return False

    def remove_temp_files(self):
        for name in os.listdir(self.source):
            path = os.path.join(self.source, name)
            logger.debug(f"[FileManager] removing {path}")
            try:
                os.remove(path)
                logger.debug(f"[FileManager] Removed {path}")
            except Exception as e:
                logger.error(f"[FileManager] Error removing {path}: {e}")

        logger.info(f"[FileManager] Temporary files in {self.source} removed.")
        return True
