#!/usr/bin/env bash
set -euo pipefail

BIN_DIR="/app/appdata/bin"
mkdir -p "${BIN_DIR}"

if [[ ! -f "${BIN_DIR}/Bento4-SDK" ]]; then
  echo "[entrypoint] Downloading Bento4 SDK..."
  curl -L -o /tmp/Bento4-SDK.zip https://cdn.hypernylium.com/mdnx-auto-dl/Bento4-SDK.zip
  unzip -q /tmp/Bento4-SDK.zip -d "${BIN_DIR}"
  rm -f /tmp/Bento4-SDK.zip
fi

if [[ ! -f "${BIN_DIR}/mdnx" ]]; then
  echo "[entrypoint] Downloading MDNX CLI..."
  curl -L -o /tmp/mdnx.zip https://cdn.hypernylium.com/mdnx-auto-dl/mdnx.zip
  unzip -q /tmp/mdnx.zip -d "${BIN_DIR}"
  rm -f /tmp/mdnx.zip
fi

chmod -R 775 "${BIN_DIR}" || true

python /app/app.py || {
  echo "app.py crashed – keeping container alive" >&2
  tail -f /dev/null
}
