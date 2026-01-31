import os
import sys
import inspect
import threading
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo
from zipfile import ZipFile, ZIP_DEFLATED

from .Vars import config, LOG_DIR, TZ


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
            str(config.app.log_level).upper(),
            LEVEL_VALUES["INFO"]
        )

        self.max_archives = config.app.max_log_archives
        self.lock = threading.Lock()

        # rotate any existing log from the previous run.
        self._rotate()
        return

    def debug(self, message: str, exc_info=None) -> None:
        """Logs a debug-level message."""
        self._log(message, level="DEBUG", exc_info=exc_info)
        return

    def info(self, message: str, exc_info=None) -> None:
        """Logs an info-level message."""
        self._log(message, level="INFO", exc_info=exc_info)
        return

    def warning(self, message: str, exc_info=None) -> None:
        """Logs a warning-level message."""
        self._log(message, level="WARNING", exc_info=exc_info)
        return

    def error(self, message: str, exc_info=None) -> None:
        """Logs an error-level message."""
        self._log(message, level="ERROR", exc_info=exc_info)
        return

    def critical(self, message: str, exc_info=None) -> None:
        """Logs a critical-level message."""
        self._log(message, level="CRITICAL", exc_info=exc_info)
        return

    def _rotate(self) -> None:
        """Archives the current log file and prunes old archives if necessary."""

        with self.lock:
            if not os.path.exists(self.log_file):
                return

            if os.path.getsize(self.log_file) == 0:
                return

            self._archive_current_log_locked()
            self._prune_archives_locked()

        return

    def _log(self, message: str, level: str = "INFO", exc_info=None) -> None:
        """Logs a message with the specified level to both terminal and log file."""

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
        now = datetime.now(ZoneInfo(TZ))
        time_str = now.strftime("%I:%M:%S %p")
        date_str = now.strftime("%d/%m/%Y")

        terminal_line = f"[{level_name}] {message}"
        logfile_line = f"[{time_str} {date_str}] [{level_name}] [{filename}<{funcname}>] - {message}"

        self._write_line(logfile_line)

        # if exc_info is provided, append a formatted traceback to the log file.
        norm = self._normalize_exc_info(exc_info)
        if norm is not None:
            try:
                traceback_text = "".join(traceback.format_exception(*norm)).rstrip("\n")
                for traceback_line in traceback_text.splitlines():
                    self._write_line(f"[{time_str} {date_str}] [{level_name}] [{filename}<{funcname}>] - {traceback_line}")
            except Exception:
                # avoid raising from the logger itself.
                pass

        print(terminal_line, file=sys.stdout, flush=True)

        return

    def _normalize_exc_info(self, exc_info):
        """Normalize exc_info into (exc_type, exc_value, tb) tuple or None."""

        if exc_info is None:
            return None

        if exc_info is True:
            return sys.exc_info()

        if isinstance(exc_info, BaseException):
            return (type(exc_info), exc_info, exc_info.__traceback__)

        if isinstance(exc_info, tuple) and len(exc_info) == 3:
            return exc_info

        return None

    def _archive_current_log_locked(self) -> None:
        """Archives the current log file into a zip with a timestamped name."""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        log_basename = os.path.basename(self.log_file)
        log_stem, _ = os.path.splitext(log_basename)

        zip_name = os.path.join(self.log_dir, f"{log_stem}_{timestamp}.zip")

        try:
            with ZipFile(zip_name, mode="w", compression=ZIP_DEFLATED) as zf:
                zf.write(self.log_file, arcname=log_basename)
        finally:
            try:
                os.remove(self.log_file)
            except FileNotFoundError:
                pass
        return

    def _prune_archives_locked(self) -> None:
        """Deletes oldest log archives if exceeding max_archives limit."""

        log_basename = os.path.basename(self.log_file)
        log_stem, _ = os.path.splitext(log_basename)

        archives = []
        for name in os.listdir(self.log_dir):
            if name.startswith(log_stem + "_") and name.endswith(".zip"):
                full_path = os.path.join(self.log_dir, name)
                archives.append(full_path)

        # sort by oldest modification time
        archives.sort(key=os.path.getmtime)

        while len(archives) > self.max_archives:
            oldest = archives.pop(0)
            try:
                os.remove(oldest)
            except FileNotFoundError:
                pass
        return

    def _write_line(self, line) -> None:
        """Writes a line to the log file with thread safety."""

        with self.lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return

    def _get_caller(self):
        """
        Returns (filename, function_name) of the caller of self._log().

        Stack frames:
        0 -> _get_caller
        1 -> _log
        2 -> info/debug/etc
        3 -> user code
        """
        try:
            stack = inspect.stack()
            if len(stack) < 4:
                return "<unknown>", "<unknown>"
            frame = stack[3].frame
        except Exception:
            return "<unknown>", "<unknown>"

        code = frame.f_code
        filename = os.path.basename(code.co_filename)
        funcname = code.co_name

        if funcname == "<module>":
            funcname = "__root__"

        return filename, funcname
