"""migrate config.json

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULT_DATA_DIR = "/data"
DEFAULT_FOLDER_STRUCTURE = "${seriesTitle}/S${season}/${seriesTitle} - S${seasonPadded}E${episodePadded}"


def upgrade():
    config_path = os.getenv("CONFIG_FILE") or "appdata/config/config.json"

    if os.path.splitext(config_path)[1].lower() != ".json":
        return

    if not os.path.isfile(config_path):
        return

    with open(config_path, "r", encoding="utf-8") as config_file:
        on_disk_config = json.load(config_file)

    if not isinstance(on_disk_config, dict):
        return

    app_section = on_disk_config.get("app")
    if not isinstance(app_section, dict):
        return

    has_legacy_data_dir = "DATA_DIR" in app_section
    has_legacy_folder_structure = "FOLDER_STRUCTURE" in app_section

    # user must have done migration themselfs or migration has already been done.
    # in any case, skip the migration to avoid overwriting any manual changes they may have made to the config.
    if not has_legacy_data_dir and not has_legacy_folder_structure:
        return

    backup_path = f"{config_path}.bak"
    shutil.copyfile(config_path, backup_path)

    legacy_dir = app_section.get("DATA_DIR") or DEFAULT_DATA_DIR
    legacy_folder_structure = app_section.get("FOLDER_STRUCTURE") or DEFAULT_FOLDER_STRUCTURE

    destinations = on_disk_config.get("destinations")
    if not isinstance(destinations, dict):
        destinations = {}
        on_disk_config["destinations"] = destinations

    # only add a destinations entry for an enabled service that does not have one yet.
    # CR_ENABLED and HIDIVE_ENABLED are the only services that existed in v2.4.1.
    if app_section.get("CR_ENABLED") is True and "crunchyroll" not in destinations:
        destinations["crunchyroll"] = {
            "dir": legacy_dir,
            "folder_structure": legacy_folder_structure,
        }

    if app_section.get("HIDIVE_ENABLED") is True and "hidive" not in destinations:
        destinations["hidive"] = {
            "dir": legacy_dir,
            "folder_structure": legacy_folder_structure,
        }

    app_section.pop("DATA_DIR", None)
    app_section.pop("FOLDER_STRUCTURE", None)

    with open(config_path, "w", encoding="utf-8") as config_file:
        json.dump(on_disk_config, config_file, indent=4, ensure_ascii=False)
        config_file.write("\n")


def downgrade():

    # one-way migration. users who need the old shape have config.json.bak.
    pass
