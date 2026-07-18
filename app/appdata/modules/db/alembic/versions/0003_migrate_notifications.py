"""migrate notification config

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-21 00:00:00.000000

"""
import os
import json
import yaml
import shutil
from typing import Sequence, Union

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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

    app_section = on_disk_config.get("app")
    if not isinstance(app_section, dict):
        return

    mutated = False

    # old single-choice users who picked "smtp" keep working with the new flag
    if app_section.get("NOTIFICATION_PREFERENCE") == "smtp" and "SMTP_ENABLED" not in app_section:
        app_section["SMTP_ENABLED"] = True
        mutated = True

    # old ntfy support used a shell script that no longer exists, so there is nothing to migrate.
    # let the user know they must set the new ntfy config.
    if app_section.get("NOTIFICATION_PREFERENCE") == "ntfy":
        print("[migration 0003] ntfy notifications now use your config file directly. Set NTFY_ENABLED and NTFY_URL in your config to keep getting ntfy notifications.")

    # these keys no longer exist in AppConfig and would fail validation if left behind
    if "NOTIFICATION_PREFERENCE" in app_section:
        app_section.pop("NOTIFICATION_PREFERENCE", None)
        mutated = True

    if "NTFY_SCRIPT_PATH" in app_section:
        app_section.pop("NTFY_SCRIPT_PATH", None)
        mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
