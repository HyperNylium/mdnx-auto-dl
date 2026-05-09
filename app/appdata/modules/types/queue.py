from pydantic import BaseModel, ConfigDict, Field


class SeriesInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series_name: str
    series_id: str | None = None
    seasons_count: str | None = None
    eps_count: str | None = None


class Episode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    episode_id: str | None = None
    episode_number: str
    episode_number_download: str | None = None
    episode_name: str

    available_dubs: list[str] = Field(default_factory=list)
    available_subs: list[str] = Field(default_factory=list)
    available_qualities: list[str] = Field(default_factory=list)

    episode_downloaded: bool = False
    episode_skip: bool = False
    has_all_dubs_subs: bool = False


class Season(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season_id: str
    season_number: str
    season_name: str
    episodes: dict[str, Episode] = Field(default_factory=dict)


class Series(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series: SeriesInfo
    seasons: dict[str, Season] = Field(default_factory=dict)


class ServiceBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    series: dict[str, Series] = Field(default_factory=dict)


class Queue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    buckets: dict[str, ServiceBucket] = Field(default_factory=dict)
