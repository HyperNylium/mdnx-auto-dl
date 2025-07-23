#!/usr/bin/env bash

# Your ntfy instance URL
NTFY_URL="https://notify.yourdomain.com/coolstuff"

exec curl -d "$@" "$NTFY_URL"
