import os
import json
import tempfile
import urllib.request
from flask import Flask, jsonify, request, send_from_directory


class _LogManager:
    def __init__(self) -> None:
        self.debug_enabled = os.getenv("WEBUI_DEBUG", "false").lower() in ("1", "true", "yes", "on")

    def info(self, msg: str) -> None:
        print(f"[webui] [INFO] {msg}", flush=True)

    def debug(self, msg: str) -> None:
        if self.debug_enabled:
            print(f"[webui] [DEBUG] {msg}", flush=True)

    def error(self, msg: str) -> None:
        print(f"[webui] [ERROR] {msg}", flush=True)


log_manager = _LogManager()


CONFIG_DIR = os.getenv("CONFIG_DIR", "/app/appdata/config")
TARGET_CONTAINER = os.getenv("TARGET_CONTAINER", "mdnx-auto-dl")
CONTROL_URL = os.getenv("CONTROL_URL", "http://mdnx-auto-dl:8090/restart")

ALLOWED_FILES = {
    "config.json": os.path.join(CONFIG_DIR, "config.json"),
    "queue.json": os.path.join(CONFIG_DIR, "queue.json"),
}

app = Flask(__name__, static_folder="static", static_url_path="/static")


log_manager.debug(
    "WebUI initialized.\n"
    f"CONFIG_DIR={CONFIG_DIR}\n"
    f"TARGET_CONTAINER={TARGET_CONTAINER}\n"
    f"ALLOWED_FILES={list(ALLOWED_FILES.keys())}"
)


def _write(path: str, text: str) -> None:
    """Write file using a temp file in the same directory."""
    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)

    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=dir_path, text=True)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        # if replace() succeeded, tmp_path wont exist.
        # If it failed, clean up.
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _normalize_json(content: str) -> str:
    """Validate JSON and return normalized pretty-printed JSON text."""
    obj = json.loads(content)
    return json.dumps(obj, indent=4, ensure_ascii=False) + "\n"


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/api/restart")
def api_restart():
    try:
        req = urllib.request.Request(CONTROL_URL, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return jsonify(ok=True, message=body.strip())
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500


@app.get("/health")
def health():
    return jsonify(ok=True)


@app.get("/api/file/<name>")
def api_read_file(name: str):
    if name not in ALLOWED_FILES:
        return jsonify(error="unsupported file"), 404

    path = ALLOWED_FILES[name]

    if not os.path.exists(path):
        log_manager.info(f"{name} not found at {path}. Returning empty JSON placeholder.")
        return jsonify(name=name, content="{\n}\n", exists=False)

    try:
        content = _read(path)
        return jsonify(name=name, content=content, exists=True)
    except Exception as e:
        log_manager.error(f"Failed to read {name} at {path}: {e}")
        return jsonify(error=f"failed to read {name}: {e}"), 500


@app.post("/api/file/<name>")
def api_write_file(name: str):
    if name not in ALLOWED_FILES:
        return jsonify(error="unsupported file"), 404

    payload = request.get_json(silent=True) or {}
    content = payload.get("content")

    if not isinstance(content, str):
        return jsonify(error="content must be a string"), 400

    try:
        formatted = _normalize_json(content)
    except json.JSONDecodeError as e:
        return jsonify(error=f"Invalid JSON: {e.msg} (line {e.lineno}, col {e.colno})"), 400
    except Exception as e:
        return jsonify(error=f"Invalid JSON: {e}"), 400

    path = ALLOWED_FILES[name]
    try:
        _write(path, formatted)
        log_manager.info(f"Saved {name} to {path}")
        return jsonify(ok=True)
    except Exception as e:
        log_manager.error(f"Failed to write {name} to {path}: {e}")
        return jsonify(error=f"failed to write {name}: {e}"), 500
