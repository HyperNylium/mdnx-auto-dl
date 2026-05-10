from pydantic import BaseModel, ConfigDict, Field


# series_id -> season_id -> list of entry strings
SeriesMap = dict[str, dict[str, list[str]]]


class MdnxRemoteSpecials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    crunchyroll: SeriesMap = Field(default_factory=dict)
    hidive: SeriesMap = Field(default_factory=dict)
    adn: SeriesMap = Field(default_factory=dict)


class ZloRemoteSpecials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    crunchyroll: SeriesMap = Field(default_factory=dict)
    hidive: SeriesMap = Field(default_factory=dict)
    adn: SeriesMap = Field(default_factory=dict)
    disneyplus: SeriesMap = Field(default_factory=dict)
    amazon: SeriesMap = Field(default_factory=dict)


class RemoteSpecialsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mdnx: MdnxRemoteSpecials = Field(default_factory=MdnxRemoteSpecials)
    zlo: ZloRemoteSpecials = Field(default_factory=ZloRemoteSpecials)
