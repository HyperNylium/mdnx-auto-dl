import os
import sqlite3


QUEUE_DB_FILE = os.getenv("QUEUE_DB_FILE", "appdata/config/queue.db")


def open_connection(db_path: str = QUEUE_DB_FILE) -> sqlite3.Connection:
    parent_dir = os.path.dirname(db_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(
        db_path,
        check_same_thread=False,
        isolation_level=None,
    )
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.close()

    return conn
