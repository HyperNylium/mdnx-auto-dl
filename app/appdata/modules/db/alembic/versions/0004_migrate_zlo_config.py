"""migrate zlo config

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-01 00:00:00.000000

"""
import os
import json
import yaml
import shutil
from typing import Sequence, Union

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


def _read_config(config_path: str):
    """Read the config file from disk and return it as a dict."""

    config_extension = os.path.splitext(config_path)[1].lower()

    with open(config_path, "r", encoding="utf-8") as config_file:
        match config_extension:
            case ".json":
                loaded_config = json.load(config_file)
            case ".yaml" | ".yml":
                loaded_config = yaml.safe_load(config_file) or {}
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
                yaml.safe_dump(config_data, config_file, sort_keys=False, allow_unicode=True, indent=4)


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
            if old_key in service_config and new_key not in service_config:
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
