"""rename zlo to cardinaldl

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-05 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from alembic import op
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TOP_LEVEL_RENAMED_KEYS = {
    "zlo": "cardinaldl",
    "zlo_cr_monitor_series_id": "cdl_cr_monitor_series_id",
    "zlo_hidive_monitor_series_id": "cdl_hidive_monitor_series_id",
    "zlo_adn_monitor_series_id": "cdl_adn_monitor_series_id"
}

APP_RENAMED_KEYS = {
    "ZLO_CR_ENABLED": "CDL_CR_ENABLED",
    "ZLO_HIDIVE_ENABLED": "CDL_HIDIVE_ENABLED",
    "ZLO_ADN_ENABLED": "CDL_ADN_ENABLED"
}

DESTINATION_RENAMED_KEYS = {
    "zlo-crunchyroll": "cdl-crunchyroll",
    "zlo-hidive": "cdl-hidive",
    "zlo-adn": "cdl-adn"
}

RENAMED_QUEUE_BUCKETS = {
    "ZLO-Crunchyroll": "CDL-Crunchyroll",
    "ZLO-HiDive": "CDL-HiDive",
    "ZLO-ADN": "CDL-ADN"
}

# every table that stores a service name in a "service" column
QUEUE_TABLES = ("series", "seasons", "episodes")

OLD_BIN_FOLDER = "/bin/zlo/"
NEW_BIN_FOLDER = "/bin/cardinaldl/"


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


def _rename_keys(target: dict, renamed_keys: dict[str, str]) -> bool:
    """Move each old key over to its new name. Returns True when something actually moved."""

    mutated = False

    for old_key, new_key in renamed_keys.items():
        if old_key not in target or new_key in target:
            continue

        # a ruamel map keeps comments so we put the new key back in the same spot
        if isinstance(target, CommentedMap):
            insert_at = list(target.keys()).index(old_key)
            comment_record = target.ca.items.pop(old_key, None)
            target.insert(insert_at, new_key, target.pop(old_key))
            if comment_record is not None:
                target.ca.items[new_key] = comment_record
        else:
            # a plain dict is a json config with no comments to keep
            target[new_key] = target.pop(old_key)

        mutated = True

    return mutated


def upgrade():
    for table_name in QUEUE_TABLES:
        for old_bucket, new_bucket in RENAMED_QUEUE_BUCKETS.items():
            op.execute(f"UPDATE {table_name} SET service = '{new_bucket}' WHERE service = '{old_bucket}'")

    config_path = _resolve_config_path()

    if not os.path.isfile(config_path):
        return

    on_disk_config = _read_config(config_path)
    if on_disk_config is None:
        return

    mutated = _rename_keys(on_disk_config, TOP_LEVEL_RENAMED_KEYS)

    app_section = on_disk_config.get("app")
    if isinstance(app_section, dict):
        if _rename_keys(app_section, APP_RENAMED_KEYS):
            mutated = True

    destinations_section = on_disk_config.get("destinations")
    if isinstance(destinations_section, dict):
        if _rename_keys(destinations_section, DESTINATION_RENAMED_KEYS):
            mutated = True

    # the binary folder moved, so any storage path still aimed at the old one has to follow it
    cardinaldl_section = on_disk_config.get("cardinaldl")
    if isinstance(cardinaldl_section, dict):
        for service_config in cardinaldl_section.values():
            if not isinstance(service_config, dict):
                continue

            storage_path = service_config.get("configPath")
            if isinstance(storage_path, str) and OLD_BIN_FOLDER in storage_path:
                service_config["configPath"] = storage_path.replace(OLD_BIN_FOLDER, NEW_BIN_FOLDER)
                mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.0005-3.1.3.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
