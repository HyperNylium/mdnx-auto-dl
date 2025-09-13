import requests

# Custom imports
from .Vars import logger, config



def scan_media_server() -> bool:
    media_server_type = config["app"]["MEDIASERVER_TYPE"]
    media_server_url = config["app"]["MEDIASERVER_URL"]
    media_server_token = config["app"]["MEDIASERVER_TOKEN"]
    media_server_url_override = config["app"]["MEDIASERVER_URL_OVERRIDE"]

    if not media_server_url or not media_server_token:
        logger.info("[MediaServerManager] Media server URL or token not configured. Skipping scan.")
        return False

    if "plex" in media_server_type.lower():
        scan_plex(media_server_url, media_server_url_override, media_server_token)

    elif "jellyfin" in media_server_type.lower():
        scan_jellyfin(media_server_url, media_server_url_override, media_server_token)

    else:
        logger.warning("[MediaServerManager] Unsupported media server type. Please use Plex or Jellyfin.")
        return False

    return True

def scan_plex(server_url: str, url_override: bool, plex_token: str) -> bool:
    server_url = server_url.rstrip('/')

    if url_override:
        url = server_url
    else:
        url = f"{server_url}/library/sections/all/refresh"

    params = {"X-Plex-Token": plex_token}

    try:
        response = requests.get(url, params=params, timeout=30)
        logger.debug(f"[MediaServerManager] Plex scan URL: {response.url}")
        response.raise_for_status()
        logger.debug(f"[MediaServerManager] Plex scan response: {response.text}")
        logger.info("[MediaServerManager] Plex scan triggered successfully.")
        return True
    except requests.RequestException as e:
        logger.error(f"Error triggering Plex scan: {e}")

    return False

def scan_jellyfin(server_url: str, url_override: bool, api_key: str) -> bool:
    server_url = server_url.rstrip('/')

    if url_override:
        url = server_url
    else:
        url = f"{server_url}/Library/Refresh"

    params = {"api_key": api_key}

    try:
        response = requests.post(url, params=params, timeout=30)
        logger.debug(f"[MediaServerManager] Jellyfin scan URL: {response.url}")
        response.raise_for_status()
        logger.debug(f"[MediaServerManager] Jellyfin scan response: {response.text}")
        logger.info("[MediaServerManager] Jellyfin scan triggered successfully.")
        return True
    except requests.RequestException as e:
        logger.error(f"Error triggering Jellyfin scan: {e}")

    return False
