#!/usr/bin/env bash

# Your ntfy instance URL
NTFY_URL="https://notify.yourdomain.com/somecoolroom"

exec curl -d "$@" "$NTFY_URL"
