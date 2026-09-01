#!/usr/bin/env bash

set -euo pipefail

USER_ID=${UID:-1000}
GROUP_ID=${GID:-1000}
USERNAME=mdnx-auto-dl
CONFIG_FILE="${CONFIG_FILE:-}"
FREEZE="${FREEZE:-false}"

if [[ -z "$CONFIG_FILE" ]]; then
  CONFIG_CANDIDATES=(
    "/app/appdata/config/config.json"
    "/app/appdata/config/config.yaml"
    "/app/appdata/config/config.yml"
  )

  for config_candidate in "${CONFIG_CANDIDATES[@]}"; do
    if [[ -f "$config_candidate" ]]; then
      CONFIG_FILE="$config_candidate"
      break
    fi
  done

  if [[ -z "$CONFIG_FILE" ]]; then
    CONFIG_FILE="/app/appdata/config/config.json"
  fi
fi

# If the config file does not exist, warn and exit
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[entrypoint] ERROR: $CONFIG_FILE not found."
  echo "[entrypoint] Please create the config file before starting the container."
  exit 1
fi

echo "[entrypoint] Starting up. Reading configuration..."

read_config() {
  local config_key="$1"
  local default_value="$2"

  CONFIG_FILE="$CONFIG_FILE" CONFIG_KEY="$config_key" DEFAULT_VALUE="$default_value" python - <<'PY'
import json
import os
from ruamel.yaml import YAML

config_file_path = os.environ["CONFIG_FILE"]
config_key = os.environ["CONFIG_KEY"]
default_value = os.environ["DEFAULT_VALUE"]

config_extension = os.path.splitext(config_file_path)[1].lower()

with open(config_file_path, "r", encoding="utf-8") as config_file:
    match config_extension:
        case ".json":
            loaded_config = json.load(config_file)
        case ".yaml" | ".yml":
            loaded_config = YAML(typ="safe").load(config_file) or {}
        case _:
            raise SystemExit(f"Unsupported config format: {config_file_path}")

if not isinstance(loaded_config, dict):
    raise SystemExit(f"Config root must be an object/dictionary in {config_file_path}")

app_config = loaded_config.get("app")
if not isinstance(app_config, dict):
    app_config = {}

value = app_config.get(config_key, default_value)

if value is None:
    value = default_value

print(value)
PY
}

purge_folder() {
  local target_dir="$1"
  shift  # remove the first argument (target_dir) from the list of arguments

  if [[ ! -d "$target_dir" ]]; then
    echo "[entrypoint] Log directory $target_dir does not exist. Nothing to purge."
    return
  fi

  echo "[entrypoint] Purging log files in $target_dir"

  local pattern
  local matches
  local count
  local total=0

  for pattern in "$@"; do
    mapfile -t matches < <(find "$target_dir" -maxdepth 1 -regextype posix-extended -type f -regex ".*/$pattern" 2>/dev/null)
    count=${#matches[@]}
    total=$((total + count))

    echo "[entrypoint]   Found $count file(s) matching '$pattern' in $target_dir"

    if (( count > 0 )); then
      if ! find "$target_dir" -maxdepth 1 -regextype posix-extended -type f -regex ".*/$pattern" -delete 2>/dev/null; then
        echo "[entrypoint]   WARNING: Could not purge '$pattern' files in $target_dir (permission issue). Continuing..."
      fi
    fi
  done

  echo "[entrypoint]   Purged $total file(s) total from $target_dir"
}

# Extract BIN_DIR (falls back to /app/appdata/bin if the key is null/absent)
BIN_DIR="$(read_config "BIN_DIR" "/app/appdata/bin")"

echo "[entrypoint] Using CONFIG_FILE=$CONFIG_FILE"
echo "[entrypoint] Using BIN_DIR=$BIN_DIR"
mkdir -p "$BIN_DIR"

# Create non-root user and start app with said user
if ! getent group "$GROUP_ID" >/dev/null; then
    groupadd -g "$GROUP_ID" "$USERNAME"
fi

if ! getent passwd "$USERNAME" >/dev/null; then
    if [[ -d "/home/$USERNAME" ]]; then
        useradd -M -u "$USER_ID" -g "$GROUP_ID" -d "/home/$USERNAME" "$USERNAME"
    else
        useradd -m -u "$USER_ID" -g "$GROUP_ID" "$USERNAME"
    fi
fi

# Purge old log files in the logs directories for both mdnx and cardinaldl tools.
purge_folder "$BIN_DIR/mdnx/logs" "latest\.log" "[0-9]+\.[0-9]+\.log"
purge_folder "$BIN_DIR/cardinaldl/config/logs" "combined\.log" "error\.log"

echo "[entrypoint] Applying ownership and permissions to /app. This can take a moment..."
chown -R "$USER_ID:$GROUP_ID" /app
chmod -R 775 /app

# Make required symlinks for CardinalDL support
ln -sfn "/app/appdata/bin/bento4/mp4decrypt" "/app/appdata/bin/cardinaldl/static/bento4/mp4decrypt"
ln -sfn "/app/appdata/bin/shaka_packager/shaka" "/app/appdata/bin/cardinaldl/static/shaka_packager/shaka"
ln -sfn "/app/appdata/bin/dovi_tool/dovi_tool" "/app/appdata/bin/cardinaldl/static/dovi_tool/dovi_tool"
ln -sfn "/app/appdata/bin/hdr10plus_tool/hdr10plus_tool" "/app/appdata/bin/cardinaldl/static/hdr10plus_tool/hdr10plus_tool"
ln -sfn "/usr/local/bin/ffmpeg" "/app/appdata/bin/cardinaldl/static/ffmpeg/ffmpeg"
ln -sfn "/usr/local/bin/ffprobe" "/app/appdata/bin/cardinaldl/static/ffmpeg/ffprobe"
ln -sfn "/usr/bin/mkvmerge" "/app/appdata/bin/cardinaldl/static/mkvmerge/mkvmerge"
ln -sfn "/usr/bin/mkvpropedit" "/app/appdata/bin/cardinaldl/static/mkvmerge/mkvpropedit"

# Check if any CardinalDL services are enabled in the config to determine if we need to fix permissions on CardinalDL paths.
CDL_ENABLED=false
for cdl_flag in CDL_CR_ENABLED CDL_HIDIVE_ENABLED CDL_ADN_ENABLED CDL_DISNEY_ENABLED CDL_NETFLIX_ENABLED CDL_AMAZON_ENABLED; do
  flag_value="$(read_config "$cdl_flag" "false")"
  if [[ "${flag_value,,}" == "true" ]]; then
    CDL_ENABLED=true
    break
  fi
done

if [[ "$CDL_ENABLED" == "true" ]]; then
  CDL_BIN_PATH="$BIN_DIR/cardinaldl/cardinaldl"
  CDL_USER_CONFIG_DIR="$BIN_DIR/cardinaldl/config"

  echo "[entrypoint] CardinalDL enabled. Fixing ownership/permissions on CardinalDL paths..."

  if [[ -f "$CDL_BIN_PATH" ]]; then
    chown "$USER_ID:$GROUP_ID" "$CDL_BIN_PATH"
    chmod 775 "$CDL_BIN_PATH"
  fi

  if [[ -d "$CDL_USER_CONFIG_DIR" ]]; then
    chown -R "$USER_ID:$GROUP_ID" "$CDL_USER_CONFIG_DIR"
    chmod -R 775 "$CDL_USER_CONFIG_DIR"
  fi
fi

echo "[entrypoint] Running database migrations via Alembic..."
gosu "$USER_ID:$GROUP_ID" bash -c "alembic -c appdata/modules/db/alembic/alembic.ini upgrade head"

# If FREEZE is true, keep the container alive without starting the app
if [[ "${FREEZE,,}" == "true" ]]; then
  echo "[entrypoint] FREEZE=true. Container will stay up without starting app.py."
  echo "[entrypoint] Use 'docker exec -it mdnx-auto-dl bash' to get a shell."
  exec tail -f /dev/null
fi

# Run as non-root user
echo "[entrypoint] Starting app.py as $USER_ID:$GROUP_ID"
exec gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py"
