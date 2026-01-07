#!/usr/bin/env sh
set -eu

USER_ID=${UID:-1000}
GROUP_ID=${GID:-1000}
USERNAME=mdnx-auto-dl
DOCKER_SOCK="${DOCKER_SOCK_PATH:-/var/run/docker.sock}"

log() { echo "[webui] $1" >&2; }

if ! getent group "$GROUP_ID" >/dev/null 2>&1; then
  addgroup -g "$GROUP_ID" "$USERNAME"
fi

if ! getent passwd "$USER_ID" >/dev/null 2>&1; then
  adduser -D -u "$USER_ID" -G "$USERNAME" "$USERNAME"
fi

mkdir -p /app/appdata/config /app/appdata/logs
chown -R "$USER_ID:$GROUP_ID" /app/appdata 2>/dev/null || true

exec gosu "$USERNAME" gunicorn -k gthread --threads 3 -w 2 --timeout 0 --graceful-timeout 30 -b 0.0.0.0:8080 app:app