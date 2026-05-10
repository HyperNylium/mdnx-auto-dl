from pydantic import BaseModel, ConfigDict, Field


# series_id -> season_id -> list of entry strings
SeriesMap = dict[str, dict[str, list[str]]]


class MdnxExtraSpecials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    crunchyroll: SeriesMap = Field(default_factory=dict)
    hidive: SeriesMap = Field(default_factory=dict)
    adn: SeriesMap = Field(default_factory=dict)


class ZloExtraSpecials(BaseModel):
    model_config = ConfigDict(extra="ignore")

    crunchyroll: SeriesMap = Field(default_factory=dict)
    hidive: SeriesMap = Field(default_factory=dict)
    adn: SeriesMap = Field(default_factory=dict)
    disneyplus: SeriesMap = Field(default_factory=dict)
    amazon: SeriesMap = Field(default_factory=dict)


class ExtraSpecialsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mdnx: MdnxExtraSpecials = Field(default_factory=MdnxExtraSpecials)
    zlo: ZloExtraSpecials = Field(default_factory=ZloExtraSpecials)
