"""rename mdnx services to the mdnx prefix

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-13 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from alembic import op
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TOP_LEVEL_RENAMED_KEYS = {
    "cr_monitor_series_id": "mdnx_cr_monitor_series_id",
    "hidive_monitor_series_id": "mdnx_hidive_monitor_series_id",
    "adn_monitor_series_id": "mdnx_adn_monitor_series_id"
}

DESTINATION_RENAMED_KEYS = {
    "crunchyroll": "mdnx-crunchyroll",
    "hidive": "mdnx-hidive",
    "adn": "mdnx-adn"
}

APP_RENAMED_KEYS = {
    "CR_ENABLED": "MDNX_CR_ENABLED",
    "CR_USERNAME": "MDNX_CR_USERNAME",
    "CR_PASSWORD": "MDNX_CR_PASSWORD",
    "CR_FORCE_REAUTH": "MDNX_CR_FORCE_REAUTH",
    "CR_SKIP_API_TEST": "MDNX_CR_SKIP_API_TEST",
    "HIDIVE_ENABLED": "MDNX_HIDIVE_ENABLED",
    "HIDIVE_USERNAME": "MDNX_HIDIVE_USERNAME",
    "HIDIVE_PASSWORD": "MDNX_HIDIVE_PASSWORD",
    "HIDIVE_FORCE_REAUTH": "MDNX_HIDIVE_FORCE_REAUTH",
    "HIDIVE_SKIP_API_TEST": "MDNX_HIDIVE_SKIP_API_TEST",
    "ADN_ENABLED": "MDNX_ADN_ENABLED",
    "ADN_USERNAME": "MDNX_ADN_USERNAME",
    "ADN_PASSWORD": "MDNX_ADN_PASSWORD",
    "ADN_FORCE_REAUTH": "MDNX_ADN_FORCE_REAUTH"
}

RENAMED_QUEUE_BUCKETS = {
    "Crunchyroll": "MDNX-Crunchyroll",
    "HiDive": "MDNX-HiDive",
    "ADN": "MDNX-ADN"
}

QUEUE_TABLES = ("series", "seasons", "episodes")


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

    # 0002 can add the old destination keys but we remove them here to keep the config clean.
    for old_destination_key in DESTINATION_RENAMED_KEYS:
        if old_destination_key in destinations_section:
            del destinations_section[old_destination_key]
            mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.0009-3.4.0.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
