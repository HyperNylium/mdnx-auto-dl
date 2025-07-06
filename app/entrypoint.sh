#!/usr/bin/env bash

set -euo pipefail

USER_ID=${UID:-1000}
GROUP_ID=${GID:-1000}
USERNAME=mdnx-auto-dl
CONFIG_FILE="${CONFIG_FILE:-/app/appdata/default/config.json}"

# Warn if the config file is the default one
if [[ "$CONFIG_PATH" == "appdata/default/config.json" ]]; then
  echo "[entrypoint] Using default config file. Please create a custom config file at 'appdata/config/config.json' to configure the application to your needs."
fi

# Extract BIN_DIR (falls back to /app/appdata/bin if the JSON key is null/absent)
BIN_DIR="$(jq -er '.app.BIN_DIR // "/app/appdata/bin"' "$CONFIG_FILE")"

echo "[entrypoint] Using CONFIG_FILE=$CONFIG_FILE"
echo "[entrypoint] Using BIN_DIR=$BIN_DIR"
mkdir -p "$BIN_DIR"

# Download Bento4 SDK
echo "[entrypoint] Fetching Bento4 SDK..."
curl -L -o /tmp/Bento4-SDK.zip https://cdn.hypernylium.com/mdnx-auto-dl/Bento4-SDK.zip
unzip -oq /tmp/Bento4-SDK.zip -d "$BIN_DIR"
rm -f /tmp/Bento4-SDK.zip

# Download MDNX CLI
echo "[entrypoint] Fetching MDNX CLI..."
curl -L -o /tmp/mdnx.zip https://cdn.hypernylium.com/mdnx-auto-dl/mdnx.zip
unzip -oq /tmp/mdnx.zip -d "$BIN_DIR"
rm -f /tmp/mdnx.zip

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

    # Run as non-root user
    # exec gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py"

    gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py" || {
        echo "app.py crashed – keeping container alive" >&2
        tail -f /dev/null
    }
else
    # Run as non-root user
    # exec gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py"

    gosu "$USER_ID:$GROUP_ID" bash -c "python /app/app.py" || {
        echo "app.py crashed – keeping container alive" >&2
        tail -f /dev/null
    }
fi