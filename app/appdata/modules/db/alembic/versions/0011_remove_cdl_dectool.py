"""remove cardinaldl dectool option

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-19 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# CardinalDL dropped --dectool and now always uses shaka from now on
REMOVED_KEY = "dectool"


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


def _remove_key(target: dict, key: str) -> bool:
    """Drop a single key from the mapping. Returns True when the key was there to remove."""

    if key not in target:
        return False

    # a ruamel map keeps a comment record for the key so clear it too
    if isinstance(target, CommentedMap):
        target.ca.items.pop(key, None)

    del target[key]
    return True


def upgrade():
    config_path = _resolve_config_path()

    if not os.path.isfile(config_path):
        return

    on_disk_config = _read_config(config_path)
    if on_disk_config is None:
        return

    cardinaldl_section = on_disk_config.get("cardinaldl")
    if not isinstance(cardinaldl_section, dict):
        return

    mutated = False

    for service_config in cardinaldl_section.values():
        if not isinstance(service_config, dict):
            continue

        if _remove_key(service_config, REMOVED_KEY):
            mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.0011-3.4.0.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
