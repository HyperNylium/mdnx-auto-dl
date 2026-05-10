from pydantic import BaseModel, ConfigDict

from .config import MdnxConfig, SeasonMonitorConfig, ZloServiceConfig


class Service(BaseModel):

    # arbitrary_types_allowed is needed to let us store the live API client instances on each Service.
    # The API client types are not defined in this module, so we cant import them here for type annotations without circular imports.
    # We could use string annotations to avoid the circular imports, but its easier to just allow arbitrary types in this one model and annotate the API client as "object | None".
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # short id used in logs and queue lookups
    service_name: str

    # the bucket name inside queue.json
    queue_bucket: str

    # human readable label for log lines
    display_name: str

    # which downloader this service uses: "mdnx" or "zlo"
    tool: str

    # live config object for this service.
    # MDNX services point at the shared MdnxConfig.
    # ZLO services point at their own ZloServiceConfig slice.
    config: MdnxConfig | ZloServiceConfig

    # live monitor dict slice for this service (series_id -> season map)
    monitor_series_id: dict[str, dict[str, SeasonMonitorConfig]]

    # the attribute name on Config that holds monitor_series_id.
    monitor_config_key: str

    # whether the user has enabled this service in the config.
    enabled: bool

    # API instance for this service.
    api: object | None = None

    @property
    def configured(self) -> bool:
        """True when the service is enabled and its API instance is attached."""

        return self.enabled and self.api is not None


class MdnxServices(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    crunchyroll: Service
    hidive: Service
    adn: Service

    def all(self) -> list[Service]:
        """Return every MDNX service as a flat list for iteration."""

        return [
            self.crunchyroll,
            self.hidive,
            self.adn
        ]


class ZloServices(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    crunchyroll: Service
    hidive: Service
    adn: Service
    disney: Service
    amazon: Service

    def all(self) -> list[Service]:
        """Return every ZLO service as a flat list for iteration."""

        return [
            self.crunchyroll,
            self.hidive,
            self.adn,
            self.disney,
            self.amazon,
        ]


class Services(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    mdnx: MdnxServices
    zlo: ZloServices

    def all(self) -> list[Service]:
        """Return every registered service as a flat list for iteration."""

        services = []
        for mdnx_service in self.mdnx.all():
            services.append(mdnx_service)
        for zlo_service in self.zlo.all():
            services.append(zlo_service)
        return services

    def get(self, service_name: str) -> Service | None:
        """Look up a service by its service_name id. Returns None if unknown."""

        for service in self.all():
            if service.service_name == service_name:
                return service
        return None
