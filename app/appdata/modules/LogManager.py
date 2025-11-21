import os
import sys
import inspect
import threading
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED

# Custom imports
from .Vars import config, LOG_DIR


LEVEL_VALUES = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


class LogManager:
    def __init__(self) -> None:
        self.log_dir = LOG_DIR
        self.log_file = os.path.join(self.log_dir, "mdnx-auto-dl.log")

        # make sure log directory exists
        os.makedirs(self.log_dir, exist_ok=True)

        # normalize log level from config (defaults to INFO)
        self.min_level = LEVEL_VALUES.get(
            str(config["app"]["LOG_LEVEL"]).upper(),
            LEVEL_VALUES["INFO"]
        )

        self.max_archives = config["app"]["MAX_LOG_ARCHIVES"]
        self.lock = threading.Lock()

        # rotate any existing log from the previous run.
        self._rotate()
        return

    def debug(self, message: str) -> None:
        self._log(message, level="DEBUG")
        return

    def info(self, message: str) -> None:
        self._log(message, level="INFO")
        return

    def warning(self, message: str) -> None:
        self._log(message, level="WARNING")
        return

    def error(self, message: str) -> None:
        self._log(message, level="ERROR")
        return

    def critical(self, message: str) -> None:
        self._log(message, level="CRITICAL")
        return

    def _log(self, message: str, level: str = "INFO") -> None:
        level_name = level.upper()
        level_value = LEVEL_VALUES.get(level_name)

        # treat empty level as INFO
        if level_value is None:
            level_name = "INFO"
            level_value = LEVEL_VALUES["INFO"]

        # level filtering
        if level_value < self.min_level:
            return

        # get caller module and function
        filename, funcname = self._get_caller()

        # timestamp
        # time_str: 6:00:00 AM
        # date_str: 11/19/2025
        now = datetime.now()
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%d/%m/%Y")

        line = f"[{time_str} {date_str}] [{level_name}] [{filename}<{funcname}>] - {message}"

        self._write_line(line)

        print(line, file=sys.stdout, flush=True)

        return

    def rotate(self) -> None:
        self._rotate()
        return

    def _rotate(self) -> None:
        with self.lock:
            if not os.path.exists(self.log_file):
                return

            if os.path.getsize(self.log_file) == 0:
                return

            self._archive_current_log_locked()
            self._prune_archives_locked()
        return

    def _archive_current_log_locked(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        log_basename = os.path.basename(self.log_file)
        log_stem, _ = os.path.splitext(log_basename)

        zip_name = os.path.join(self.log_dir, f"{log_stem}_{timestamp}.zip")

        try:
            with ZipFile(zip_name, mode="w", compression=ZIP_DEFLATED) as zf:
                # store as "mdnx-auto-dl.log" inside the zip
                zf.write(self.log_file, arcname=log_basename)
        finally:
            try:
                os.remove(self.log_file)
            except FileNotFoundError:
                pass
        return

    def _prune_archives_locked(self) -> None:
        log_basename = os.path.basename(self.log_file)
        log_stem, _ = os.path.splitext(log_basename)

        archives = []
        for name in os.listdir(self.log_dir):
            if name.startswith(log_stem + "_") and name.endswith(".zip"):
                full_path = os.path.join(self.log_dir, name)
                archives.append(full_path)

        # Sort by modification time (oldest first)
        archives.sort(key=os.path.getmtime)

        while len(archives) > self.max_archives:
            oldest = archives.pop(0)
            try:
                os.remove(oldest)
            except FileNotFoundError:
                pass
        return

    def _write_line(self, line) -> None:
        with self.lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return

    def _get_caller(self):
        """
        Returns (filename, function_name) of the caller of self.log().

        Because this function itself is another stack frame, we look
        two frames up:
          0 -> _get_caller
          1 -> log
          2 -> user code that called log()
        """
        try:
            stack = inspect.stack()
            if len(stack) < 3:
                return "<unknown>", "<unknown>"

            frame = stack[2].frame
        except Exception:
            return "<unknown>", "<unknown>"

        code = frame.f_code
        filename = os.path.basename(code.co_filename)
        funcname = code.co_name

        if funcname == "<module>":
            funcname = "__root__"

        return filename, funcname
