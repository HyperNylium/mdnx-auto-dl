import sys
import time
import uuid
import requests
from urllib.parse import urlencode

from .Globals import log_manager
from .Vars import (
    config,
    update_app_config, format_duration
)

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
            log_manager.error("MEDIASERVER_URL is not set or empty. Please set it in config.json. Exiting...")
            sys.exit(1)

        # normalize server URL
        if isinstance(self.server_url, str):
            self.server_url = self.server_url.strip().rstrip("/")

        # per-process client id (Plex requires a client identifier)
        self.client_id = str(uuid.uuid4())

        # PIN state
        self.pin_id = None
        self.pin_code = None
        self.pin_started_at = None
        self.pin_url_logged = False

        log_manager.info(f"PLEX API initialized with: URL: {self.server_url}")

    def wait_for_auth(self, max_wait_seconds: int = 600, poll_interval: float = 1.0) -> bool:
        """Wait for user to authorize app via Plex PIN process."""

        if self._verify_token(self.token):
            return True

        if not (self.pin_id and self.pin_code):
            self._create_and_log_pin()

        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            if self._verify_token(self.token):
                return True

            if self.pin_id and self.pin_code:
                new_token = self._poll_pin_for_token(self.pin_id, self.pin_code)
                if new_token:
                    self._store_token(new_token)
                    self._clear_pin_state()
                    log_manager.info("Authorization completed. Token stored.")
                    return True

            if self.pin_started_at and (time.time() - self.pin_started_at > PLEX_PIN_TIMEOUT_SECONDS):
                log_manager.info("PIN timed out. Generating a new one.")
                self._clear_pin_state()
                self._create_and_log_pin()

            time.sleep(poll_interval)

        log_manager.error(f"Authorization timed out after {format_duration(max_wait_seconds)}.")
        return False

    def scan_library(self) -> bool:
        """If configured, trigger a library scan on the Plex Media Server."""

        if not self.server_url:
            log_manager.info("MEDIASERVER_URL not configured. Skipping scan.")
            return False

        if not self._verify_token(self.token):
            log_manager.info("No valid token yet.")
            return False

        # if user has set URL override, use whatever is in MEDIASERVER_URL
        if self.url_override:
            log_manager.info("MEDIASERVER_URL_OVERRIDE is true. Using whatever is in MEDIASERVER_URL for scan endpoint.")
            url = self.server_url
        else:
            log_manager.info("Using standard Plex scan URL for all libraries.")
            url = f"{self.server_url}/library/sections/all/refresh"

        try:
            resp = requests.get(
                url,
                headers=self._headers(include_token=True),
                timeout=30
            )
            log_manager.debug(f"Scan status={resp.status_code}")
            resp.raise_for_status()
            log_manager.info("Scan triggered successfully.")
            return True
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 401:
                log_manager.debug("401 Unauthorized. Token invalid or lacks permission.")
            else:
                log_manager.error(f"HTTP error: {e}")
        except requests.RequestException as e:
            log_manager.error(f"Request failed: {e}")
        return False

    def _headers(self, include_token: bool) -> dict:
        """Generate headers for Plex API requests."""

        headers = {
            "Accept": "application/json",
            "X-Plex-Product": PLEX_PRODUCT_NAME,
            "X-Plex-Client-Identifier": self.client_id,
        }
        if include_token and self.token:
            headers["X-Plex-Token"] = self.token
        return headers

    def _verify_token(self, token) -> bool:
        """Verify if the provided token is valid by making a request to Plex API."""

        if not token:
            return False

        try:
            resp = requests.get(
                f"{PLEX_API_BASE}/user",
                headers=self._headers(include_token=True),
                timeout=10
            )
            log_manager.debug(f"Verify token status={resp.status_code}")
            return resp.status_code == 200
        except requests.RequestException as e:
            log_manager.warning(f"Token verify error (network?): {e}")
            return False

    def _create_and_log_pin(self) -> None:
        """Create a new PIN and log the authorization URL."""

        pin_id, code, auth_url = self._start_pin()

        self.pin_id = pin_id
        self.pin_code = code
        self.pin_started_at = time.time()

        if not self.pin_url_logged:
            log_manager.info(f"Open this URL in a browser to authorize the app:\n{auth_url}")
            self.pin_url_logged = True

    def _start_pin(self):
        """Start the PIN authorization process."""

        resp = requests.post(
            f"{PLEX_API_BASE}/pins",
            headers=self._headers(include_token=False),
            data={"strong": "true"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        pin_id = data["id"]
        code = data["code"]

        auth_url = PLEX_API_AUTH_URL + "#?" + urlencode(
            {
                "clientID": self.client_id,
                "code": code,
                "context[device][product]": PLEX_PRODUCT_NAME,
            }
        )
        return pin_id, code, auth_url

    def _poll_pin_for_token(self, pin_id, code):
        """Poll the Plex API to check if the PIN has been authorized and retrieve the auth token."""

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
            log_manager.error(f"PIN poll error: {e}")
            return None

    def _store_token(self, token) -> None:
        """Store the token in config.json."""

        ok = update_app_config("MEDIASERVER_TOKEN", token)
        if not ok:
            log_manager.error("Failed to persist MEDIASERVER_TOKEN to config.")
        self.token = token

    def _clear_pin_state(self) -> None:
        """Clear the current PIN state."""

        self.pin_id = None
        self.pin_code = None
        self.pin_started_at = None
        self.pin_url_logged = False


class JELLYFIN_API:
    def __init__(self) -> None:
        raw_url = config["app"]["MEDIASERVER_URL"]
        self.api_key = config["app"]["MEDIASERVER_TOKEN"]
        self.server_url = None

        # normalize server URL
        if isinstance(raw_url, str):
            self.server_url = raw_url.strip().rstrip("/")

        if self.server_url is None or self.server_url == "":
            log_manager.error("MEDIASERVER_URL is not set or empty. Please set it in config.json. Exiting...")
            sys.exit(1)

        if self.api_key is None or self.api_key == "":
            log_manager.error("MEDIASERVER_TOKEN (API key) is not set or empty. Please set it in config.json. Exiting...")
            sys.exit(1)

        log_manager.info(f"Initialized (URL: {self.server_url})")

    def scan_library(self) -> bool:
        """If configured, trigger a library scan on the Jellyfin Media Server."""

        if not self.server_url:
            log_manager.info("MEDIASERVER_URL not configured. Skipping scan.")
            return False

        if not self.api_key:
            log_manager.info("MEDIASERVER_TOKEN (API key) not configured. Skipping scan.")
            return False

        url = f"{self.server_url}/Library/Refresh"
        try:
            resp = requests.post(
                url,
                params={"api_key": self.api_key},
                timeout=30
            )
            log_manager.debug(f"Scan URL: {resp.url}")
            resp.raise_for_status()
            log_manager.debug(f"Response: {resp.text}")
            log_manager.info("Scan triggered successfully.")
            return True
        except requests.RequestException as e:
            log_manager.error(f"Error triggering scan: {e}")
            return False


def _get_media_server() -> PLEX_API | JELLYFIN_API | None:
    """Get or create the media server API instance based on config and save it globally."""

    global MEDIA_SERVER_INSTANCE

    if MEDIA_SERVER_INSTANCE is not None:
        return MEDIA_SERVER_INSTANCE

    server_type = config["app"]["MEDIASERVER_TYPE"]

    # no media server configured in config.json
    if server_type is None:
        return None

    if server_type == "plex":
        MEDIA_SERVER_INSTANCE = PLEX_API()
    elif server_type == "jellyfin":
        MEDIA_SERVER_INSTANCE = JELLYFIN_API()
    elif server_type == "":
        log_manager.error("MEDIASERVER_TYPE is not set. Please set it to 'plex' or 'jellyfin' in config.json. Exiting...")
        sys.exit(1)
    else:
        log_manager.error(f"Unsupported media server type: {server_type}. Supported: 'plex' or 'jellyfin'. Exiting...")
        sys.exit(1)

    return MEDIA_SERVER_INSTANCE


# functions to call from other modules
def mediaserver_auth(max_wait_seconds: int = 600, poll_interval: float = 1.0) -> bool:
    """Perform media server authentication if needed."""

    inst = _get_media_server()

    if inst is None:
        return False

    if isinstance(inst, PLEX_API):
        return inst.wait_for_auth(max_wait_seconds, poll_interval)

    # for jellyfin, no auth process needed because of the API key.
    # just return success.
    return True


def mediaserver_scan_library() -> bool:
    """Trigger a media server library scan if configured."""

    inst = _get_media_server()

    if inst is None:
        return False

    return inst.scan_library()
