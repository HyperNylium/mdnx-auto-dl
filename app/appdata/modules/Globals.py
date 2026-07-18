import threading

from .LogManager import LogManager
log_manager = LogManager()

from .FileManager import FileManager  # ruff:ignore[module-import-not-at-top-of-file]
file_manager = FileManager()

from .QueueManager import QueueManager  # ruff:ignore[module-import-not-at-top-of-file]
queue_manager = QueueManager()

from .RemoteSpecials import RemoteSpecials  # ruff:ignore[module-import-not-at-top-of-file]
remote_specials = RemoteSpecials()

# Global stop event for threads to check and exit gracefully
stop_event = threading.Event()
