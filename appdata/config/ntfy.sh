#!/usr/bin/env bash

# Your ntfy instance URL
NTFY_URL="https://notify.yourdomain.com/coolstuff"

SUBJECT="$1"
MESSAGE="$2"

exec curl -H "Title: $SUBJECT" -d "$MESSAGE" "$NTFY_URL"