#!/usr/bin/env bash

set -euo pipefail

APP_FILE="/app/app.py"
MIGRATIONS_DIR="/app/appdata/migrations"
MIGRATION_STATE_FILE="${MIGRATION_STATE_FILE:-/app/appdata/config/migrations.json}"

REQUIRED_MIGRATIONS=()

APP_VERSION="$(APP_FILE="$APP_FILE" python - <<'PY'
import os

app_file_path = os.environ["APP_FILE"]
app_version = None

with open(app_file_path, "r", encoding="utf-8") as app_file:
    for raw_line in app_file:
        stripped_line = raw_line.strip()

        if not stripped_line.startswith("__VERSION__"):
            continue

        if "=" not in stripped_line:
            continue

        _, version_value = stripped_line.split("=", 1)
        version_value = version_value.strip()

        if version_value.startswith(("\"", "'")) and version_value.endswith(("\"", "'")):
            app_version = version_value[1:-1]
            break

if app_version is None or app_version == "":
    raise SystemExit("Could not find __VERSION__ in app.py")

print(app_version)
PY
)"

echo "[migration_runner] Detected app version: $APP_VERSION"

if [[ ! -f "$MIGRATION_STATE_FILE" ]]; then
    cat > "$MIGRATION_STATE_FILE" <<'EOF'
{
    "completed_versions": []
}
EOF

    echo "[migration_runner] Created migration state file at $MIGRATION_STATE_FILE"
fi

MIGRATION_REQUIRED=false
for required_version in "${REQUIRED_MIGRATIONS[@]}"; do
    if [[ "$required_version" == "$APP_VERSION" ]]; then
        MIGRATION_REQUIRED=true
        break
    fi
done

if [[ "$MIGRATION_REQUIRED" == false ]]; then
    echo "[migration_runner] No migration is required for version $APP_VERSION"
    exit 0
fi

if jq -e --arg version "$APP_VERSION" '.completed_versions | index($version) != null' "$MIGRATION_STATE_FILE" >/dev/null 2>&1; then
    echo "[migration_runner] Migration for version $APP_VERSION was already completed before. Skipping."
    exit 0
fi

MIGRATION_SCRIPT_PATH="${MIGRATIONS_DIR}/${APP_VERSION}_migration.sh"

echo "[migration_runner] Looking for migration script at $MIGRATION_SCRIPT_PATH"

if [[ ! -f "$MIGRATION_SCRIPT_PATH" ]]; then
    echo "[migration_runner] ERROR: required migration script was not found."
    exit 1
fi

chmod +x "$MIGRATION_SCRIPT_PATH"

echo "[migration_runner] Running migration script for version $APP_VERSION"
"$MIGRATION_SCRIPT_PATH"
echo "[migration_runner] Migration script finished for version $APP_VERSION"

TEMP_STATE_FILE="$(mktemp)"

jq --arg version "$APP_VERSION" '
    if (.completed_versions | index($version)) == null then
        .completed_versions += [$version]
    else
        .
    end
' "$MIGRATION_STATE_FILE" > "$TEMP_STATE_FILE"

mv "$TEMP_STATE_FILE" "$MIGRATION_STATE_FILE"

echo "[migration_runner] Marked migration as completed for version $APP_VERSION"
echo "[migration_runner] Migration flow complete for version $APP_VERSION"
