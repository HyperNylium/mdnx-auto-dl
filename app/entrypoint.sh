#!/usr/bin/env bash

set -euo pipefail

USER_ID=${UID:-1000}
GROUP_ID=${GID:-1000}
USERNAME=mdnx-auto-dl
CONFIG_FILE="${CONFIG_FILE:-/app/__appdata__/config/config.json}"

BENTO4_URL="${BENTO4_URL:-https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/__appdata__/bin/Bento4-SDK.zip}"
MDNX_URL="${MDNX_URL:-https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/master/app/__appdata__/bin/mdnx.zip}"

# If config.json doesn't exist, warn and exit
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[entrypoint] ERROR: $CONFIG_FILE not found."
  echo "[entrypoint] Please create the config file before starting the container."
  exit 1
fi

# Extract BIN_DIR (falls back to /app/__appdata__/bin if the JSON key is null/absent)
BIN_DIR="$(jq -er '.app.BIN_DIR // "/app/__appdata__/bin"' "$CONFIG_FILE")"

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
if grep -qEi 'microsoft|wsl' /proc/version 2>/dev/null; then
    IS_LINUX=true
else
    IS_LINUX=$(uname | grep -qi linux && echo true || echo false)
fi

if [ "$IS_LINUX" = true ]; then
    if ! getent group "$GROUP_ID" >/dev/null; then
        groupadd -g "$GROUP_ID" "$USERNAME"
    fi
    if ! id -u "$USER_ID" >/dev/null 2>&1; then
        useradd -m -u "$USER_ID" -g "$GROUP_ID" "$USERNAME"
    fi
    chown -R "$USER_ID:$GROUP_ID" /app
    chmod -R 775 /app
fi

NTFY_SCRIPT_PATH="$(jq -er '.app.NTFY_SCRIPT_PATH // ""' "$CONFIG_FILE")"

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
