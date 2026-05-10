import os
import re
import yaml
import requests
from pydantic import ValidationError

from .Globals import log_manager
from .types.remote_specials import RemoteSpecialsConfig


# digits only like "7"
_NUMBER_RE = re.compile(r"^\d+$")

# digits-digits like "3-5"
_RANGE_RE = re.compile(r"^(\d+)-(\d+)$")

# tag for ZLO episode IDs in YAML like "id:G7XK4M2NA"
_ID_PREFIX = "id:"


def _expand_range(range_match: re.Match) -> set[str]:
    """Expand a 'start-end' regex match into a set of episode-number strings."""

    start = int(range_match.group(1))
    end = int(range_match.group(2))
    if start > end:
        start, end = end, start

    numbers: set[str] = set()
    current = start
    while current <= end:
        numbers.add(str(current))
        current += 1

    return numbers


class RemoteSpecials:
    def __init__(self) -> None:
        self._url = os.getenv("REMOTE_SPECIALS_URL", "https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/dev/remote-specials.yaml").strip()

        # (downloader, service, series_id, season_id) -> (numbers_set, ids_set)
        self._overrides: dict[tuple[str, str, str, str], tuple[set[str], set[str]]] = {}

    def _classify_mdnx_entry(self, entry: str) -> tuple[set[str], set[str]]:
        """Classify an MDNX entry."""

        if _NUMBER_RE.match(entry):
            return ({entry}, set())

        range_match = _RANGE_RE.match(entry)
        if range_match:
            return (_expand_range(range_match), set())

        log_manager.warning(f"MDNX entry '{entry}' is not a number or range. Dropping.")
        return (set(), set())

    def _classify_zlo_entry(self, entry: str) -> tuple[set[str], set[str]]:
        """Classify a ZLO entry."""

        if entry.startswith(_ID_PREFIX):
            stripped = entry[len(_ID_PREFIX):]
            if stripped == "":
                log_manager.warning(f"ZLO entry '{entry}' has empty id. Dropping.")
                return (set(), set())
            return (set(), {stripped})

        if _NUMBER_RE.match(entry):
            return ({entry}, set())

        range_match = _RANGE_RE.match(entry)
        if range_match:
            return (_expand_range(range_match), set())

        log_manager.warning(f"ZLO entry '{entry}' is not a number, range, or id-tagged value. Dropping.")
        return (set(), set())

    def _ingest_service(self, downloader: str, service: str, series_map, classifier) -> int:
        """Walk one service's tree, write to self._overrides, return how many entries landed."""

        entry_count = 0

        if not isinstance(series_map, dict):
            log_manager.warning(f"{downloader}.{service} is not a mapping. Skipping.")
            return entry_count

        for series_id, season_map in series_map.items():
            if not isinstance(season_map, dict):
                log_manager.warning(f"{downloader}.{service}.{series_id} is not a mapping. Skipping.")
                continue

            for season_id, entries in season_map.items():
                if not isinstance(entries, list):
                    log_manager.warning(f"{downloader}.{service}.{series_id}.{season_id} is not a list. Skipping.")
                    continue

                numbers_acc: set[str] = set()
                ids_acc: set[str] = set()

                for entry in entries:
                    if not isinstance(entry, str):
                        log_manager.warning(f"non-string entry under {downloader}.{service}.{series_id}.{season_id}: {entry!r}. Dropping.")
                        continue

                    numbers, ids = classifier(entry)
                    if numbers or ids:
                        entry_count += 1
                        numbers_acc.update(numbers)
                        ids_acc.update(ids)

                if numbers_acc or ids_acc:
                    key = (downloader, service, str(series_id), str(season_id))
                    self._overrides[key] = (numbers_acc, ids_acc)

        return entry_count

    def refresh(self) -> None:
        """Fetch REMOTE_SPECIALS_URL, validate, and rebuild state."""

        self._overrides.clear()

        if self._url.lower() == "false" or self._url == "":
            log_manager.debug("remote specials URL is disabled. Feature disabled this pass.")
            return

        try:
            resp = requests.get(self._url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as fetch_error:
            log_manager.warning(f"fetch failed for {self._url}: {fetch_error}. Feature disabled this pass.")
            return

        try:
            raw = yaml.safe_load(resp.text)
        except yaml.YAMLError as parse_error:
            log_manager.warning(f"YAML parse failed: {parse_error}. Feature disabled this pass.")
            return

        if raw is None:
            log_manager.debug("file is empty. Feature disabled this pass.")
            return

        if not isinstance(raw, dict):
            log_manager.warning("top-level value is not a mapping. Feature disabled this pass.")
            return

        # drop unknown top-level keys so only mdnx/zlo reach Pydantic
        for top_key in list(raw.keys()):
            if top_key not in ("mdnx", "zlo"):
                log_manager.warning(f"unknown top-level key '{top_key}'. Ignoring.")
                del raw[top_key]

        try:
            cfg = RemoteSpecialsConfig.model_validate(raw)
        except ValidationError as validation_error:
            log_manager.warning(f"schema validation failed: {validation_error}. Feature disabled this pass.")
            return

        total = 0
        total += self._ingest_service("mdnx", "crunchyroll", cfg.mdnx.crunchyroll, self._classify_mdnx_entry)
        total += self._ingest_service("mdnx", "hidive", cfg.mdnx.hidive, self._classify_mdnx_entry)
        total += self._ingest_service("mdnx", "adn", cfg.mdnx.adn, self._classify_mdnx_entry)
        total += self._ingest_service("zlo", "crunchyroll", cfg.zlo.crunchyroll, self._classify_zlo_entry)
        total += self._ingest_service("zlo", "hidive", cfg.zlo.hidive, self._classify_zlo_entry)
        total += self._ingest_service("zlo", "adn", cfg.zlo.adn, self._classify_zlo_entry)
        total += self._ingest_service("zlo", "disneyplus", cfg.zlo.disneyplus, self._classify_zlo_entry)
        total += self._ingest_service("zlo", "amazon", cfg.zlo.amazon, self._classify_zlo_entry)

        log_manager.info(f"loaded {total} entries across {len(self._overrides)} season slots.")

    def is_remote_special(self, downloader: str, service: str, series_id: str, season_id: str, episode_number: str, episode_id: str | None = None) -> bool:
        """True if this episode is in the override file for this downloader/service."""

        key = (downloader, service, str(series_id), str(season_id))
        bucket = self._overrides.get(key)
        if bucket is None:
            return False

        numbers, ids = bucket

        if episode_number in numbers:
            return True

        if episode_id is not None and episode_id in ids:
            return True

        return False
