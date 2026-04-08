#!/usr/bin/env bash

set -euo pipefail

USER_ID=${UID:-1000}
GROUP_ID=${GID:-1000}
USERNAME=mdnx-auto-dl
CONFIG_FILE="${CONFIG_FILE:-}"

BENTO4_URL="${BENTO4_URL:-https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/Bento4-SDK.zip}"
MDNX_URL="${MDNX_URL:-https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/appdata/bin/mdnx.zip}"

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

read_config_app_value() {
  local config_key="$1"
  local default_value="$2"

  CONFIG_FILE="$CONFIG_FILE" CONFIG_KEY="$config_key" DEFAULT_VALUE="$default_value" python - <<'PY'
import json
import os
import yaml

config_file_path = os.environ["CONFIG_FILE"]
config_key = os.environ["CONFIG_KEY"]
default_value = os.environ["DEFAULT_VALUE"]

config_extension = os.path.splitext(config_file_path)[1].lower()

with open(config_file_path, "r", encoding="utf-8") as config_file:
    match config_extension:
        case ".json":
            loaded_config = json.load(config_file)
        case ".yaml" | ".yml":
            loaded_config = yaml.safe_load(config_file) or {}
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

# Extract BIN_DIR (falls back to /app/appdata/bin if the key is null/absent)
BIN_DIR="$(read_config_app_value "BIN_DIR" "/app/appdata/bin")"

echo "[entrypoint] Using CONFIG_FILE=$CONFIG_FILE"
echo "[entrypoint] Using BIN_DIR=$BIN_DIR"
mkdir -p "$BIN_DIR"

# Bento4 SDK
if [[ -f "$BIN_DIR/Bento4-SDK.zip" ]]; then
  echo "[entrypoint] Extracting Bento4-SDK from $BIN_DIR/Bento4-SDK.zip..."
  unzip -oq "$BIN_DIR/Bento4-SDK.zip" -d "$BIN_DIR"
  rm -f "$BIN_DIR/Bento4-SDK.zip"
elif [[ -d "$BIN_DIR/Bento4-SDK" ]]; then
  echo "[entrypoint] Bento4-SDK.zip missing, but extracted directory found. Skipping unzip."
else
  echo "[entrypoint] Bento4 SDK not found locally. Downloading from '$BENTO4_URL'..."
  tmp_zip="$BIN_DIR/.Bento4-SDK.zip.tmp"
  if curl -fL --retry 5 --retry-all-errors --connect-timeout 10 -o "$tmp_zip" "$BENTO4_URL"; then
    mv "$tmp_zip" "$BIN_DIR/Bento4-SDK.zip"
    echo "[entrypoint] Extracting downloaded Bento4 SDK..."
    unzip -oq "$BIN_DIR/Bento4-SDK.zip" -d "$BIN_DIR"
    rm -f "$BIN_DIR/Bento4-SDK.zip"
  else
    echo "[entrypoint] ERROR: failed to download Bento4 SDK from $BENTO4_URL" >&2
    rm -f "$tmp_zip" || true
    echo "[entrypoint] Please run 'docker compose down && docker compose up -d' to fix this."
    exit 1
  fi
fi

# MDNX CLI
if [[ -f "$BIN_DIR/mdnx.zip" ]]; then
  echo "[entrypoint] Extracting MDNX CLI from $BIN_DIR/mdnx.zip..."
  unzip -oq "$BIN_DIR/mdnx.zip" -d "$BIN_DIR"
  rm -f "$BIN_DIR/mdnx.zip"
elif [[ -f "$BIN_DIR/mdnx/aniDL" ]]; then
  echo "[entrypoint] mdnx.zip missing, but aniDL binary found. Assuming folder exists as well. Skipping unzip."
else
  echo "[entrypoint] MDNX CLI not found locally. Downloading from '$MDNX_URL'..."
  tmp_zip="$BIN_DIR/.mdnx.zip.tmp"
  if curl -fL --retry 5 --retry-all-errors --connect-timeout 10 -o "$tmp_zip" "$MDNX_URL"; then
    mv "$tmp_zip" "$BIN_DIR/mdnx.zip"
    echo "[entrypoint] Extracting downloaded MDNX CLI..."
    unzip -oq "$BIN_DIR/mdnx.zip" -d "$BIN_DIR"
    rm -f "$BIN_DIR/mdnx.zip"
  else
    echo "[entrypoint] ERROR: failed to download MDNX CLI from $MDNX_URL" >&2
    rm -f "$tmp_zip" || true
    echo "[entrypoint] Please run 'docker compose down && docker compose up -d' to fix this."
    exit 1
  fi
fi

# Create non-root user and start app with said user
if ! getent group "$GROUP_ID" >/dev/null; then
    groupadd -g "$GROUP_ID" "$USERNAME"
fi

if ! id -u "$USER_ID" >/dev/null 2>&1; then
    useradd -m -u "$USER_ID" -g "$GROUP_ID" "$USERNAME"
fi

chown -R "$USER_ID:$GROUP_ID" /app
chmod -R 775 /app

# Run migrations if needed
echo "[entrypoint] Checking for required migrations..."
gosu "$USER_ID:$GROUP_ID" bash -c "/app/migration_runner.sh"

NTFY_SCRIPT_PATH="$(read_config_app_value "NTFY_SCRIPT_PATH" "")"

if [[ -n "$NTFY_SCRIPT_PATH" && -f "$NTFY_SCRIPT_PATH" ]]; then
  echo "[entrypoint] Found ntfy script at $NTFY_SCRIPT_PATH. Making it executable..."
  chmod +x "$NTFY_SCRIPT_PATH"
else
  echo "[entrypoint] No ntfy script at $NTFY_SCRIPT_PATH. Skipping chmod."
fi

# Run as non-root user
echo "[entrypoint] Starting app.py as $USER_ID:$GROUP_ID"
exec gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py"

# For debugging docker container.
# gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py" || {
#     echo "app.py crashed – keeping container alive" >&2
#     tail -f /dev/null
# }
