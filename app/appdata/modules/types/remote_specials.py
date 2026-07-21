import re
from typing import Annotated
from pydantic import (
    Field, field_validator,
    BaseModel, ConfigDict, StringConstraints
)


# a number with no leading zeros like "7" or "13"
NUMBER_PATTERN = r"(0|[1-9]\d*)"

# tag for ZLO episode IDs in YAML like "id:G7XK4M2NA"
ID_PREFIX = "id:"

# highest episode number a range may reach, so a typo cannot expand into millions of entries
MAX_EPISODE = 5000

# digits-digits like "3-5"
RANGE_RE = re.compile(rf"^{NUMBER_PATTERN}-{NUMBER_PATTERN}$")

# series id straight from the parser. only checked for being non-blank
Series = Annotated[str, StringConstraints(min_length=1)]

# season key like "S0" or "S12"
Season = Annotated[str, StringConstraints(pattern=r"^S\d+$")]

# MDNX entry, a number or a range
MdnxEntry = Annotated[str, StringConstraints(pattern=rf"^{NUMBER_PATTERN}(-{NUMBER_PATTERN})?$")]

# ZLO entry, a number, a range, or an episode id
ZloEntry = Annotated[str, StringConstraints(pattern=rf"^({NUMBER_PATTERN}(-{NUMBER_PATTERN})?|{ID_PREFIX}.+)$")]

# series_id -> season_id -> list of entry strings
MdnxSeriesMap = dict[Series, dict[Season, list[MdnxEntry]]]
ZloSeriesMap = dict[Series, dict[Season, list[ZloEntry]]]

# either downloader's series map, for code that handles both
SeriesMap = MdnxSeriesMap | ZloSeriesMap

# (downloader, service, series_id, season_id)
OverrideKey = tuple[str, str, str, str]

# (episode numbers, ZLO episode ids)
OverrideBucket = tuple[set[str], set[str]]

# every season slot we found overrides for
OverridesMap = dict[OverrideKey, OverrideBucket]


class ServiceSpecials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("*")
    @classmethod
    def check_series_map(cls, series_map: SeriesMap) -> SeriesMap:
        """Check what the type aliases cannot express on their own."""

        for series_id, season_map in series_map.items():
            if len(season_map) == 0:  # no seasons in the series
                raise ValueError(f"series '{series_id}' has no seasons")

            for season_id, entries in season_map.items():
                if len(entries) == 0:  # no entries/episodes in the season
                    raise ValueError(f"'{series_id}.{season_id}' has no entries")

                if len(entries) != len(set(entries)):  # duplicate entries/episodes in the season
                    raise ValueError(f"'{series_id}.{season_id}' has duplicate entries")

                for entry in entries:
                    range_match = RANGE_RE.match(entry)
                    if range_match is None:
                        continue

                    start = int(range_match.group(1))
                    end = int(range_match.group(2))

                    if start > end:  # ranges must count up, not down
                        raise ValueError(f"'{series_id}.{season_id}' range '{entry}' counts backwards")

                    if end > MAX_EPISODE:  # ranges cannot go past 5000
                        raise ValueError(f"'{series_id}.{season_id}' range '{entry}' goes past episode {MAX_EPISODE}")

        return series_map


class MdnxRemoteSpecials(ServiceSpecials):
    crunchyroll: MdnxSeriesMap = Field(default_factory=dict)
    hidive: MdnxSeriesMap = Field(default_factory=dict)
    adn: MdnxSeriesMap = Field(default_factory=dict)


class ZloRemoteSpecials(ServiceSpecials):
    crunchyroll: ZloSeriesMap = Field(default_factory=dict)
    hidive: ZloSeriesMap = Field(default_factory=dict)
    adn: ZloSeriesMap = Field(default_factory=dict)


class RemoteSpecialsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mdnx: MdnxRemoteSpecials = Field(default_factory=MdnxRemoteSpecials)
    zlo: ZloRemoteSpecials = Field(default_factory=ZloRemoteSpecials)
