"""convert season_override and year values to integers

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-10 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from ruamel.yaml import YAML

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


MONITOR_SECTIONS = (
    "mdnx_cr_monitor_series_id",
    "mdnx_hidive_monitor_series_id",
    "mdnx_adn_monitor_series_id",
    "cdl_cr_monitor_series_id",
    "cdl_hidive_monitor_series_id",
    "cdl_adn_monitor_series_id",
    "cdl_disney_monitor_series_id",
    "cdl_netflix_monitor_series_id",
    "cdl_amazon_monitor_series_id"
)

SERIES_LEVEL_KEYS = ("series_name", "year")


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

    mutated = False

    for section_key in MONITOR_SECTIONS:
        monitor_section = on_disk_config.get(section_key)
        if not isinstance(monitor_section, dict):
            continue

        for series_key, series_config in monitor_section.items():
            if not isinstance(series_config, dict):
                continue

            # the series-level year is now a whole number so convert any text value to an int
            year_value = series_config.get("year")
            if isinstance(year_value, str):
                # attempt to convert the year to an integer if it represents a whole number
                try:
                    year_number = float(year_value.strip())
                    new_year = int(year_number) if year_number.is_integer() else None
                except ValueError:
                    new_year = None

                if new_year is not None:
                    series_config["year"] = new_year
                    mutated = True
                else:
                    # drop the non-numeric year so the series uses the year reported by the service
                    del series_config["year"]
                    print(f"[migration 0014] dropped non-numeric year {year_value!r} in {section_key}/{series_key}. That series will use the year reported by the service unless overridden again.")
                    mutated = True

            # iterate over each season within the series and convert any season_override values to integers if possible
            for season_key, season_config in series_config.items():
                # skip non-season entries and malformed season configs
                if season_key in SERIES_LEVEL_KEYS or not isinstance(season_config, dict):
                    continue

                # skip entries that dont have a season_override key
                if "season_override" not in season_config:
                    continue

                current = season_config["season_override"]
                if current is None or (isinstance(current, int) and not isinstance(current, bool)):
                    continue

                # attempt to convert the current value to an integer if it represents a whole number
                try:
                    number = float(str(current).strip())
                    new_value = int(number) if number.is_integer() else None
                except ValueError:
                    new_value = None

                if new_value is not None:
                    season_config["season_override"] = new_value
                    mutated = True
                    continue

                # drop the non-numeric season_override so the season will use its auto-assigned number
                del season_config["season_override"]
                print(f"[migration 0014] dropped non-numeric season_override {current!r} in {section_key}/{series_key}/{season_key}. That season will use its auto-assigned number unless overridden again.")
                mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.0014-3.5.1.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
