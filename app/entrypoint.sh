#!/usr/bin/env bash

set -euo pipefail

USER_ID=${UID:-1000}
GROUP_ID=${GID:-1000}
USERNAME=mdnx-auto-dl
CONFIG_FILE="${CONFIG_FILE:-/app/appdata/config/config.json}"

# If config.json doesn't exist, fetch a default copy
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "[entrypoint] $CONFIG_FILE not found. Downloading default config.json..."

  # Make sure the parent directory exists
  mkdir -p "$(dirname "$CONFIG_FILE")"

  # Download the default file
  curl -fsSL https://raw.githubusercontent.com/HyperNylium/mdnx-auto-dl/refs/heads/main/appdata/config/config.json -o "$CONFIG_FILE" || {
      echo "[entrypoint] Download failed - aborting."
      exit 1
    }

  echo "[entrypoint] Default config written to $CONFIG_FILE. At some point, modify the file to your liking."
fi

# Extract BIN_DIR (falls back to /app/appdata/bin if the JSON key is null/absent)
BIN_DIR="$(jq -er '.app.BIN_DIR // "/app/appdata/bin"' "$CONFIG_FILE")"

echo "[entrypoint] Using CONFIG_FILE=$CONFIG_FILE"
echo "[entrypoint] Using BIN_DIR=$BIN_DIR"
mkdir -p "$BIN_DIR"

# Extract deps
echo "[entrypoint] Extracting Bento4 SDK from $BIN_DIR/Bento4-SDK.zip..."
unzip -oq "$BIN_DIR/Bento4-SDK.zip" -d "$BIN_DIR"
rm -f "$BIN_DIR/Bento4-SDK.zip"

echo "[entrypoint] Extracting MDNX CLI from $BIN_DIR/mdnx.zip..."
unzip -oq "$BIN_DIR/mdnx.zip" -d "$BIN_DIR"
rm -f "$BIN_DIR/mdnx.zip"

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