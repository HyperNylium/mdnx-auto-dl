import os
import time
import json
import subprocess
from shutil import move as shmove

# Custom imports
from .Vars import logger
from .Vars import TEMP_DIR, DATA_DIR, CODE_TO_LOCALE
from .Vars import sanitize

class FileHandler:
    def __init__(self):
        self.source = TEMP_DIR
        self.dest = DATA_DIR
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

    def probe_streams(self, file_path: str):
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", file_path]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error(f"[FileHandler] ffprobe error on {file_path}: {result.stderr}")
            return set(), set()

        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            logger.error(f"[FileHandler] ffprobe JSON decode error on {file_path}: {e}")
            return set(), set()

        audio_langs = set()
        sub_langs = set()

        for stream in data.get("streams", []):
            tags = stream.get("tags", {})
            lang = str(tags.get("language", "None")).strip().lower()

            if stream.get("codec_type") == "audio":
                audio_langs.add(lang)

            elif stream.get("codec_type") == "subtitle":
                # map iso-639 code to locale if known
                # Example, "eng" to "en", "jpn" to "ja"
                if lang in CODE_TO_LOCALE:
                    sub_langs.add(CODE_TO_LOCALE[lang])
                else:
                    sub_langs.add(lang)

        return audio_langs, sub_langs
