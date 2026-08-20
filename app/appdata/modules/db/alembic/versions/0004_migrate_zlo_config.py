"""migrate zlo config

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-01 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ZLO_RENAMED_KEYS = {
    "q": "quality",
    "qf": "qualityfallback"
}


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

    zlo_section = on_disk_config.get("zlo")
    if not isinstance(zlo_section, dict):
        return

    mutated = False

    # rename the old key on each service block that still uses it
    for service_config in zlo_section.values():
        if not isinstance(service_config, dict):
            continue

        for old_key, new_key in ZLO_RENAMED_KEYS.items():
            if old_key not in service_config or new_key in service_config:
                continue

            # a ruamel map keeps comments so we put the new key back in the same spot
            if isinstance(service_config, CommentedMap):
                insert_at = list(service_config.keys()).index(old_key)
                comment_record = service_config.ca.items.pop(old_key, None)
                service_config.insert(insert_at, new_key, service_config.pop(old_key))
                if comment_record is not None:
                    service_config.ca.items[new_key] = comment_record
            else:
                # a plain dict is a json config with no comments to keep
                service_config[new_key] = service_config.pop(old_key)

            mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
