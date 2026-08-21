"""rename cardinaldl quality flags

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-20 00:00:00.000000

"""
import os
import json
import shutil
from typing import Sequence, Union
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_DEFAULT_QUALITY = "1080p@avc"
NEW_DEFAULT_VIDEOQUALITY = "1080p@@sdr"

CODEC_RENAMES = {
    "avc": "h264",
    "hvc": "hevc",
    "vp9": "vp9",
    "av1": "av1"
}

CONFIG_RENAMES = {
    "qualityfallback": "fallback",
    "dubLang": "dublang",
    "forceSubFormat": "forcesubformat",
    "tempPath": "temppath",
    "configPath": "configpath"
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


def _migrate_quality(old_quality) -> tuple[str, bool | None]:
    """Convert the old quality string into the new videoquality string and determine if hybrid should be set."""

    text = str(old_quality).strip()

    # if the old default quality is present, we want to change it to the new default videoquality
    if text == OLD_DEFAULT_QUALITY:
        return NEW_DEFAULT_VIDEOQUALITY, None

    if text == "":
        return "", None

    parts = text.split("@")
    resolution = parts[0].strip()
    codec = parts[1].strip().lower() if len(parts) > 1 else ""

    # tbh i cant remember if the pre-3.9.24 CLIs supported hybrid or not, but if they did it was a literal @hybrid suffix so we can just check for that
    if codec == "hybrid":
        return resolution, True

    # dvh meant hevc with dolby vision so it splits into a codec slot and a range slot now
    if codec == "dvh":
        return f"{resolution}@hevc@dv", None

    if codec in CODEC_RENAMES:
        return f"{resolution}@{CODEC_RENAMES[codec]}", None

    if codec == "":
        return resolution, None

    # an unknown codec is left as it was so the config pattern check can flag it later
    return text, None


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

        # quality -> videoquality translating the value along the way
        if "quality" in service_config and "videoquality" not in service_config:
            new_videoquality, hybrid_flag = _migrate_quality(service_config.get("quality"))
            _rename_keys(service_config, {"quality": "videoquality"})
            service_config["videoquality"] = new_videoquality

            # only a leftover @hybrid gives us a hybrid flag to write
            if hybrid_flag is not None and "hybrid" not in service_config:
                service_config["hybrid"] = hybrid_flag

            mutated = True

        # the rest just change name and keep their value
        if _rename_keys(service_config, CONFIG_RENAMES):
            mutated = True

    if not mutated:
        return

    backup_path = f"{config_path}.0006-3.2.1.bak"
    shutil.copyfile(config_path, backup_path)

    _write_config(config_path, on_disk_config)


def downgrade():

    # one-way migration. users who need the old shape have a .bak of their config.
    pass
