from .API.MDNX import _shared as mdnx_shared
from .API.ZLO7 import _shared as zlo_shared
from .Globals import log_manager
from .Vars import SERVICES
from .types.queue import Episode
from .types.service import Service


TOOL_MODULES = {
    "mdnx": mdnx_shared,
    "zlo": zlo_shared
}


def _resolve(service: str) -> tuple[Service | None, object | None]:
    """Resolve a service name string to (Service, tool_module)."""

    normalized = service.strip().lower()
    service_obj = SERVICES.get(normalized)
    if service_obj is None:
        log_manager.error(f"Unknown service '{service}'.")
        return None, None
    return service_obj, TOOL_MODULES[service_obj.tool]


def select_dubs(service: str, episode: Episode, dub_overrides: list[str] | None = None):
    """Dispatch dub selection to the right per-tool module."""

    service_obj, tool_module = _resolve(service)
    if service_obj is None:
        return False
    return tool_module.select_dubs(service_obj, episode, dub_overrides)


def select_subs(service: str, episode: Episode, sub_overrides: list[str] | None = None):
    """Dispatch sub selection to the right per-tool module."""

    service_obj, tool_module = _resolve(service)
    if service_obj is None:
        return None
    return tool_module.select_subs(service_obj, episode, sub_overrides)


def get_wanted_dubs_and_subs(service: str, series_id: str, season_id: str | None) -> tuple[set, set]:
    """Dispatch wanted-tracks lookup to the right per-tool module."""

    service_obj, tool_module = _resolve(service)
    if service_obj is None:
        return set(), set()
    return tool_module.get_wanted_dubs_and_subs(service_obj, series_id, season_id)


def probe_streams(file_path: str, service: str) -> tuple[set, set]:
    """Dispatch ffprobe stream mapping to the right per-tool module."""

    service_obj, tool_module = _resolve(service)
    if service_obj is None:
        return set(), set()
    return tool_module.probe_streams(file_path)
