import os
import re
import yaml
import requests
from collections.abc import Callable
from pydantic import ValidationError

from .Globals import log_manager
from .types.remote_specials import (
    ID_PREFIX, RANGE_RE,
    RemoteSpecialsConfig, OverrideBucket, OverridesMap, SeriesMap
)


class RemoteSpecials:
    def __init__(self) -> None:
        self.url = os.getenv("REMOTE_SPECIALS_URL", "https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/remote-specials.yaml").strip()
        self.cache_path = "appdata/config/remote-specials-cache.yaml"

        # (downloader, service, series_id, season_id) -> (numbers_set, ids_set)
        self.overrides: OverridesMap = {}

    def _expand_range(self, range_match: re.Match[str]) -> set[str]:
        """Expand a 'start-end' regex match into a set of episode-number strings."""

        start = int(range_match.group(1))
        end = int(range_match.group(2))

        numbers: set[str] = set()
        current = start
        while current <= end:
            numbers.add(str(current))
            current += 1

        return numbers

    def _classify_mdnx_entry(self, entry: str) -> OverrideBucket:
        """Classify an MDNX entry."""

        range_match = RANGE_RE.match(entry)
        if range_match:
            return (self._expand_range(range_match), set())

        return ({entry}, set())

    def _classify_zlo_entry(self, entry: str) -> OverrideBucket:
        """Classify a ZLO entry."""

        if entry.startswith(ID_PREFIX):
            return (set(), {entry[len(ID_PREFIX):]})

        range_match = RANGE_RE.match(entry)
        if range_match:
            return (self._expand_range(range_match), set())

        return ({entry}, set())

    def _ingest_service(self, downloader: str, service: str, series_map: SeriesMap, classifier: Callable[[str], OverrideBucket]) -> int:
        """Walk one service's tree, write to self.overrides, return how many entries landed."""

        entry_count = 0

        for series_id, season_map in series_map.items():
            for season_id, entries in season_map.items():
                season_numbers: set[str] = set()
                season_ids: set[str] = set()

                for entry in entries:
                    numbers, ids = classifier(entry)
                    entry_count += 1
                    season_numbers.update(numbers)
                    season_ids.update(ids)

                key = (downloader, service, series_id, season_id)
                self.overrides[key] = (season_numbers, season_ids)

        return entry_count

    def _read_cache(self) -> str | None:
        """Read the cached specials file."""

        if not os.path.exists(self.cache_path):
            return None

        try:
            with open(self.cache_path, "r", encoding="utf-8") as cache_file:
                return cache_file.read()
        except (OSError, UnicodeDecodeError) as read_error:
            log_manager.warning(f"Could not read cache at {self.cache_path}: {read_error}.")
            return None

    def _write_cache(self, text: str) -> None:
        """Write a new cached specials file."""

        temp_path = f"{self.cache_path}.tmp"

        try:
            with open(temp_path, "w", encoding="utf-8") as cache_file:
                cache_file.write(text)
            os.replace(temp_path, self.cache_path)
        except OSError as write_error:
            log_manager.warning(f"Could not write cache to {self.cache_path}: {write_error}.")

    def _parse_specials(self, text: str, source_label: str) -> RemoteSpecialsConfig | None:
        """Turn specials YAML text into a validated config."""

        try:
            raw = yaml.safe_load(text)
        except yaml.YAMLError as parse_error:
            log_manager.warning(f"YAML parse failed for {source_label} file: {parse_error}.")
            return None

        if raw is None:
            log_manager.warning(f"Empty {source_label} file.")
            return None

        if not isinstance(raw, dict):
            log_manager.warning(f"Top-level value is not a mapping in {source_label} file.")
            return None

        # drop unknown top-level keys so only mdnx/zlo reach Pydantic
        for top_key in list(raw.keys()):
            if top_key not in ("mdnx", "zlo"):
                log_manager.warning(f"Unknown top-level key '{top_key}' in {source_label} file. Ignoring.")
                del raw[top_key]

        try:
            return RemoteSpecialsConfig.model_validate(raw)
        except ValidationError as validation_error:
            log_manager.warning(f"Schema validation failed for {source_label} file: {validation_error}.")
            return None

    def refresh(self) -> None:
        """Fetch REMOTE_SPECIALS_URL, validate, and rebuild state. Falls back to the cached copy when the remote file cannot be used."""

        self.overrides.clear()

        if self.url.lower() == "false" or self.url == "":
            log_manager.debug("Remote specials URL is disabled. Feature disabled this pass.")
            return

        remote_text = None

        try:
            resp = requests.get(self.url, timeout=10)
            resp.raise_for_status()
            resp.encoding = "utf-8"
            remote_text = resp.text
        except requests.RequestException as fetch_error:
            log_manager.warning(f"Fetch failed for {self.url}: {fetch_error}.")

        specials = None
        if remote_text is not None:
            specials = self._parse_specials(remote_text, "remote")

        if specials is not None:
            self._write_cache(remote_text)
        else:
            cached_text = self._read_cache()
            if cached_text is None:
                log_manager.warning("No usable cached copy. Feature disabled this pass.")
                return

            specials = self._parse_specials(cached_text, "cache")
            if specials is None:
                log_manager.warning(f"Cached copy at {self.cache_path} is unusable. Feature disabled this pass.")
                return

            log_manager.warning(f"Using cached remote specials from {self.cache_path}.")

        total = 0
        total += self._ingest_service("mdnx", "crunchyroll", specials.mdnx.crunchyroll, self._classify_mdnx_entry)
        total += self._ingest_service("mdnx", "hidive", specials.mdnx.hidive, self._classify_mdnx_entry)
        total += self._ingest_service("mdnx", "adn", specials.mdnx.adn, self._classify_mdnx_entry)
        total += self._ingest_service("zlo", "crunchyroll", specials.zlo.crunchyroll, self._classify_zlo_entry)
        total += self._ingest_service("zlo", "hidive", specials.zlo.hidive, self._classify_zlo_entry)
        total += self._ingest_service("zlo", "adn", specials.zlo.adn, self._classify_zlo_entry)

        log_manager.info(f"Loaded {total} entries across {len(self.overrides)} season slots.")

    def is_remote_special(self, downloader: str, service: str, series_id: str, season_id: str, episode_number: str, episode_id: str | None = None) -> bool:
        """True if this episode is in the override file for this downloader/service."""

        key = (downloader, service, series_id, season_id)
        bucket = self.overrides.get(key)
        if bucket is None:
            return False

        numbers, ids = bucket

        if episode_number in numbers:
            return True

        if episode_id is not None and episode_id in ids:
            return True

        return False
