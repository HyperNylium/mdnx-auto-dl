"""restructure extra_features to be keyed by service

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-08 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# old shape: extra_features.<feature>.services.<service> = {...}
# new shape: extra_features.services.<service>.<feature> = {...}
OLD_FEATURE_KEYS = ("trackforge", "transcoding")


def _resolve_config_path() -> str:
    """Determine the config file path to use, checking environment variable and default locations."""

    env_config_path = os.getenv("CONFIG_FILE")
    if env_config_path:
        return env_config_path

    default_config_paths = [
        "appdata/config/config.json",
        "appdata/config/config.yaml",
        "appdata/config/config.yml"
    ]

    for default_config_path in default_config_paths:
        if os.path.exists(default_config_path):
            return default_config_path

    return default_config_paths[0]


def _make_yaml() -> YAML:
    """Create a ruamel.yaml YAML handler with specific formatting options."""

    yaml_handler = YAML()
    yaml_handler.preserve_quotes = True
    yaml_handler.allow_unicode = True
    yaml_handler.width = 4096
    yaml_handler.indent(mapping=4, sequence=6, offset=4)
    return yaml_handler


def _read_config(config_path: str):
    """Read the config file from disk and return it as a dict."""

    config_extension = os.path.splitext(config_path)[1].lower()

    with open(config_path, "r", encoding="utf-8") as config_file:
        match config_extension:
            case ".json":
                loaded_config = json.load(config_file)
            case ".yaml" | ".yml":
                loaded_config = _make_yaml().load(config_file)
            case _:
                return None

    if not isinstance(loaded_config, dict):
        return None

    return loaded_config


def _write_config(config_path: str, config_data: dict) -> None:
    """Write the given config data dict to disk in the appropriate format based on file extension."""

    config_extension = os.path.splitext(config_path)[1].lower()

    with open(config_path, "w", encoding="utf-8") as config_file:
        match config_extension:
            case ".json":
                json.dump(config_data, config_file, indent=4, ensure_ascii=False)
                config_file.write("\n")
            case ".yaml" | ".yml":
                _make_yaml().dump(config_data, config_file)


def upgrade():
    config_path = _resolve_config_path()

    if not os.path.isfile(config_path):
        return

    on_disk_config = _read_config(config_path)
    if on_disk_config is None:
        return

    extra_features = on_disk_config.get("extra_features")
    if not isinstance(extra_features, dict):
        return

    # only migrate when an old style feature section is actually present
    has_old_section = False
    for feature_key in OLD_FEATURE_KEYS:
        if isinstance(extra_features.get(feature_key), dict):
            has_old_section = True
            break

    if not has_old_section:
        return

    use_ruamel = isinstance(extra_features, CommentedMap)
    new_services = CommentedMap() if use_ruamel else {}

    def service_entry(service_name: str):
        if service_name not in new_services:
            new_services[service_name] = CommentedMap() if use_ruamel else {}
        return new_services[service_name]

    # move each old feature section into the per-service entry it belongs to
    for feature_key in OLD_FEATURE_KEYS:
        feature_section = extra_features.get(feature_key)
        if not isinstance(feature_section, dict):
            continue

        feature_services = feature_section.get("services")
        if not isinstance(feature_services, dict):
            continue

        for service_name, service_config in feature_services.items():
            service_entry(service_name)[feature_key] = service_config

    # keep anything that is already in the new style services section
    existing_services = extra_features.get("services")
    if isinstance(existing_services, dict):
        for service_name, service_config in existing_services.items():
            entry = service_entry(service_name)
            if isinstance(service_config, dict):
                for feature_key, feature_config in service_config.items():
                    if feature_key not in entry:
                        entry[feature_key] = feature_config

    # drop the old feature keys and store the rebuilt services map
    for old_key in OLD_FEATURE_KEYS:
        if old_key in extra_features:
            if isinstance(extra_features, CommentedMap):
                extra_features.ca.items.pop(old_key, None)
            del extra_features[old_key]

    extra_features["services"] = new_services

    backup_path = f"{config_path}.0013-3.4.2.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
