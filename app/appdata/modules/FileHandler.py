import os
import time
import signal
from shutil import move as shmove
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .Vars import logger, config



class FileHandler:
    def __init__(self):
        self.source = config["app"]["TEMP_DIR"]
        self.dest = config["app"]["DATA_DIR"]
        self.extension = ".mkv"
        self.readyCheckInterval = 1       # seconds between size checks
        self.readyStableSeconds = 5       # how long size must remain unchanged
        self.readyTimeout = 300           # give up after 5 minutes
        self.moveRetries = 3              # number of retries for move operation
        self.retryDelay = 5               # seconds between move attempts

        # set up watchdog observer with a plain handler
        handler = FileSystemEventHandler()
        handler.on_created = self.onCreated
        self.observer = Observer()
        self.observer.schedule(handler, self.source, recursive=False)

        logger.info(f"[FileHandler] Initialized with\nSource: {self.source}\nDestination: {self.dest}")

    def onCreated(self, event):
        # ignore dirs and non .mkv files
        if event.is_directory or not event.src_path.lower().endswith(self.extension):
            return

        path = event.src_path
        logger.info(f"[FileHandler] Detected new {self.extension} file: {path}")

        if self.waitForReady(path):
            name = os.path.basename(path)
            targetPath = os.path.join(self.dest, name)

            if self.moveWithRetries(path, targetPath):
                logger.info(f"[FileHandler] Moved {path} to {targetPath}")
                # verify
                if os.path.exists(targetPath) and not os.path.exists(path):
                    logger.info("[FileHandler] Move verified successfully.")
                else:
                    logger.error("[FileHandler] Post move verification failed.")
            else:
                logger.error(f"[FileHandler] Failed to move {path} after {self.moveRetries} attempts.")
        else:
            logger.warning(f"[FileHandler] File not ready within {self.readyTimeout} seconds: {path}")

    def waitForReady(self, path):
        lastSize = -1
        stableTime = 0
        start = time.time()

        while time.time() - start < self.readyTimeout:
            try:
                size = os.path.getsize(path)
            except Exception as e:
                logger.error(f"[FileHandler] Error accessing {path}: {e}")
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
                logger.error(f"[FileHandler] Attempt {attempt}. Move failed: {e}")
                time.sleep(self.retryDelay)
        return False

    def start(self):
        logger.info(f"[FileHandler] Starting monitor: {self.source} to {self.dest}")
        self.observer.start()

        def shutdown(signum, frame):
            logger.info(f"[FileHandler] Received signal {signum}. Stopping monitor...")
            self.observer.stop()

        # catch both Ctrl-C and Dockers SIGTERM
        signal.signal(signal.SIGINT, shutdown)
        signal.signal(signal.SIGTERM, shutdown)

        self.observer.join()
        logger.info("[FileHandler] Monitor stopped cleanly.")