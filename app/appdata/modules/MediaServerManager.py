import sys
import time
import uuid
import requests
from urllib.parse import urlencode


# Custom imports
from .Vars import (
    logger, config,
    update_app_config, format_duration
)

# These dont need to be changed, hence they are constants
PLEX_API_BASE = "https://plex.tv/api/v2"
PLEX_API_AUTH_URL = "https://app.plex.tv/auth"
PLEX_PRODUCT_NAME = "mdnx-auto-dl"
PLEX_PIN_TIMEOUT_SECONDS = 180
MEDIA_SERVER_INSTANCE = None  # holds the PLEX_API or JELLYFIN_API class instance once created


class PLEX_API:
    def __init__(self) -> None:
        self.token = config["app"]["MEDIASERVER_TOKEN"]
        self.server_url = config["app"]["MEDIASERVER_URL"]
        self.url_override = config["app"]["MEDIASERVER_URL_OVERRIDE"]

        if self.server_url is None or self.server_url == "":
            logger.error("[MediaServerManager][PLEX_API] MEDIASERVER_URL is not set or empty. Please set it in config.json. Exiting...")
            sys.exit(1)

        if isinstance(self.server_url, str):
            self.server_url = self.server_url.strip().rstrip("/")

        # Per-process client id (Plex requires a client identifier)
        self.client_id = str(uuid.uuid4())

        # PIN state
        self.pin_id = None
        self.pin_code = None
        self.pin_started_at = None
        self.pin_url_logged = False

        logger.info(f"[MediaServerManager][PLEX_API] PLEX API initialized with: URL: {self.server_url}")

    def wait_for_auth(self, max_wait_seconds: int = 600, poll_interval: float = 1.0) -> bool:
        if self._verify_token(self.token):
            return True

        if not (self.pin_id and self.pin_code):
            self._create_and_log_pin()

        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            if self._verify_token(self.token):
                return True

            if self.pin_id and self.pin_code:
                new_token = self._poll_pin_for_token_once(self.pin_id, self.pin_code)
                if new_token:
                    self._store_token(new_token)
                    self._clear_pin_state()
                    logger.info("[MediaServerManager][PLEX_API] Authorization completed. Token stored.")
                    return True

            if self.pin_started_at and (time.time() - self.pin_started_at > PLEX_PIN_TIMEOUT_SECONDS):
                logger.info("[MediaServerManager][PLEX_API] PIN timed out. Generating a new one.")
                self._clear_pin_state()
                self._create_and_log_pin()

            time.sleep(poll_interval)

        logger.error(f"[MediaServerManager][PLEX_API] Authorization timed out after {format_duration(max_wait_seconds)}.")
        return False

    def scan_library(self) -> bool:
        if not self.server_url:
            logger.info("[MediaServerManager][PLEX_API] MEDIASERVER_URL not configured. Skipping scan.")
            return False

        if not self._verify_token(self.token):
            logger.info("[MediaServerManager][PLEX_API] No valid token yet.")
            return False

        if self.url_override:
            logger.info("[MediaServerManager][PLEX_API] MEDIASERVER_URL_OVERRIDE is true. Using whatever is in MEDIASERVER_URL for scan endpoint.")
            url = self.server_url
        else:
            logger.info("[MediaServerManager][PLEX_API] Using standard Plex scan URL for all libraries.")
            url = f"{self.server_url}/library/sections/all/refresh"

        try:
            resp = requests.get(url, headers=self._headers(include_token=True), timeout=30)
            logger.debug(f"[MediaServerManager][PLEX_API] Scan status={resp.status_code}")
            resp.raise_for_status()
            logger.info("[MediaServerManager][PLEX_API] Scan triggered successfully.")
            return True
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 401:
                logger.error("[MediaServerManager][PLEX_API] 401 Unauthorized. Token invalid or lacks permission.")
            else:
                logger.error(f"[MediaServerManager][PLEX_API] HTTP error: {e}")
        except requests.RequestException as e:
            logger.error(f"[MediaServerManager][PLEX_API] Request failed: {e}")
        return False

    def _headers(self, include_token: bool) -> dict:
        headers = {
            "Accept": "application/json",
            "X-Plex-Product": PLEX_PRODUCT_NAME,
            "X-Plex-Client-Identifier": self.client_id,
        }
        if include_token and self.token:
            headers["X-Plex-Token"] = self.token
        return headers

    def _verify_token(self, token) -> bool:
        if not token:
            return False
        try:
            resp = requests.get(f"{PLEX_API_BASE}/user", headers=self._headers(include_token=True), timeout=10)
            logger.debug(f"[MediaServerManager][PLEX_API] Verify token status={resp.status_code}")
            return resp.status_code == 200
        except requests.RequestException as e:
            logger.warning(f"[MediaServerManager][PLEX_API] Token verify error (network?): {e}")
            return False

    def _create_and_log_pin(self) -> None:
        pin_id, code, auth_url = self._start_pin()
        self.pin_id, self.pin_code, self.pin_started_at = pin_id, code, time.time()
        if not self.pin_url_logged:
            logger.info(f"[MediaServerManager][PLEX_API] Open this URL in a browser to authorize the app:\n{auth_url}")
            self.pin_url_logged = True

    def _start_pin(self):
        resp = requests.post(
            f"{PLEX_API_BASE}/pins",
            headers=self._headers(include_token=False),
            data={"strong": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        pin_id, code = data["id"], data["code"]
        auth_url = PLEX_API_AUTH_URL + "#?" + urlencode(
            {
                "clientID": self.client_id,
                "code": code,
                "context[device][product]": PLEX_PRODUCT_NAME,
            }
        )
        return pin_id, code, auth_url

    def _poll_pin_for_token_once(self, pin_id, code):
        try:
            resp = requests.get(
                f"{PLEX_API_BASE}/pins/{pin_id}",
                headers=self._headers(include_token=False),
                params={"code": code},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("authToken")
        except requests.RequestException as e:
            logger.debug(f"[MediaServerManager][PLEX_API] PIN poll error: {e}")
            return None

    def _store_token(self, token) -> None:
        ok = update_app_config("MEDIASERVER_TOKEN", token)
        if not ok:
            logger.error("[MediaServerManager][PLEX_API] Failed to persist MEDIASERVER_TOKEN to config.")
        self.token = token

    def _clear_pin_state(self) -> None:
        self.pin_id = None
        self.pin_code = None
        self.pin_started_at = None
        self.pin_url_logged = False


class JELLYFIN_API:
    def __init__(self) -> None:
        raw_url = config["app"]["MEDIASERVER_URL"]
        self.server_url = raw_url.rstrip("/") if isinstance(raw_url, str) and raw_url.strip() else None
        self.api_key = config["app"]["MEDIASERVER_TOKEN"]

        if self.server_url is None or self.server_url == "":
            logger.error("[MediaServerManager][JELLYFIN_API] MEDIASERVER_URL is not set or empty. Please set it in config.json. Exiting...")
            sys.exit(1)
        if self.api_key is None or self.api_key == "":
            logger.error("[MediaServerManager][JELLYFIN_API] MEDIASERVER_TOKEN (API key) is not set or empty. Please set it in config.json. Exiting...")
            sys.exit(1)

        logger.info(f"[MediaServerManager][JELLYFIN_API] Initialized (URL: {self.server_url})")

    def scan_library(self) -> bool:
        if not self.server_url:
            logger.info("[MediaServerManager][JELLYFIN_API] MEDIASERVER_URL not configured. Skipping scan.")
            return False

        if not self.api_key:
            logger.info("[MediaServerManager][JELLYFIN_API] MEDIASERVER_TOKEN (API key) not configured. Skipping scan.")
            return False

        url = f"{self.server_url}/Library/Refresh"
        try:
            resp = requests.post(url, params={"api_key": self.api_key}, timeout=30)
            logger.debug(f"[MediaServerManager][JELLYFIN_API] Scan URL: {resp.url}")
            resp.raise_for_status()
            logger.debug(f"[MediaServerManager][JELLYFIN_API] Response: {resp.text}")
            logger.info("[MediaServerManager][JELLYFIN_API] Scan triggered successfully.")
            return True
        except requests.RequestException as e:
            logger.error(f"[MediaServerManager][JELLYFIN_API] Error triggering scan: {e}")
            return False


def _get_media_server():
    global MEDIA_SERVER_INSTANCE

    if MEDIA_SERVER_INSTANCE is not None:
        return MEDIA_SERVER_INSTANCE

    server_type = config["app"]["MEDIASERVER_TYPE"]

    # No media server configured in config.json
    if server_type is None:
        return None

    if server_type == "plex":
        MEDIA_SERVER_INSTANCE = PLEX_API()
    elif server_type == "jellyfin":
        MEDIA_SERVER_INSTANCE = JELLYFIN_API()
    elif server_type == "":
        logger.error("[MediaServerManager] MEDIASERVER_TYPE is not set. Please set it to 'plex' or 'jellyfin' in config.json. Exiting...")
        sys.exit(1)
    else:
        logger.error(f"[MediaServerManager] Unsupported media server type: {server_type}. Supported: 'plex' or 'jellyfin'. Exiting...")
        sys.exit(1)

    return MEDIA_SERVER_INSTANCE


# Functions to call from other modules
def mediaserver_auth(max_wait_seconds: int = 600, poll_interval: float = 1.0) -> bool:
    inst = _get_media_server()
    if inst is None:
        return False
    if isinstance(inst, PLEX_API):
        return inst.wait_for_auth(max_wait_seconds, poll_interval)
    return True


def mediaserver_scan_library() -> bool:
    inst = _get_media_server()
    if inst is None:
        return False
    return inst.scan_library()
