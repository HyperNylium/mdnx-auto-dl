#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="${CONFIG_FILE:-/app/appdata/config/config.json}"

echo "[migration:2.4.0] Starting migration"

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "[migration:2.4.0] ERROR: config file not found at $CONFIG_FILE"
    exit 1
fi

timestamp="$(date +%Y%m%d_%H%M%S)"
config_backup_path="${CONFIG_FILE}.${timestamp}.bak"
temp_config_file="$(mktemp)"

cp "$CONFIG_FILE" "$config_backup_path"
echo "[migration:2.4.0] Backed up config.json to $config_backup_path"

jq '
    def add_blacklist_item($season_map; $season_id; $blacklist_item):
        ($season_map[$season_id] // {}) as $existing_season_config
        | ($existing_season_config.blacklists // []) as $existing_blacklists
        | if ($existing_blacklists | index("*")) != null then
            $season_map
          elif $blacklist_item == "*" then
            $season_map + {
                ($season_id): ($existing_season_config + {
                    "blacklists": ["*"]
                })
            }
          elif ($existing_blacklists | index($blacklist_item)) != null then
            $season_map
          else
            $season_map + {
                ($season_id): ($existing_season_config + {
                    "blacklists": ($existing_blacklists + [$blacklist_item])
                })
            }
          end;

    def convert_series_rules:
        if type == "object" then
            .
        elif type == "array" then
            reduce .[] as $raw_rule (
                {};
                if ($raw_rule | type) != "string" then
                    .
                else
                    ($raw_rule | gsub("^\\s+|\\s+$"; "")) as $rule_text
                    | if $rule_text == "" then
                        .
                      elif ($rule_text | test("^S:[^:]+$")) then
                        ($rule_text | capture("^S:(?<season_id>[^:]+)$")) as $match
                        | add_blacklist_item(.; $match.season_id; "*")
                      elif ($rule_text | test("^S:[^:]+:E:[0-9]+$")) then
                        ($rule_text | capture("^S:(?<season_id>[^:]+):E:(?<episode_num>[0-9]+)$")) as $match
                        | add_blacklist_item(.; $match.season_id; $match.episode_num)
                      elif ($rule_text | test("^S:[^:]+:E:[0-9]+-[0-9]+$")) then
                        ($rule_text | capture("^S:(?<season_id>[^:]+):E:(?<episode_start>[0-9]+)-(?<episode_end>[0-9]+)$")) as $match
                        | add_blacklist_item(.; $match.season_id; ($match.episode_start + "-" + $match.episode_end))
                      else
                        .
                      end
                end
            )
        elif type == "string" then
            [.] | convert_series_rules
        else
            {}
        end;

    def convert_monitor_map:
        if type != "object" then
            {}
        else
            with_entries(
                .value = (.value | convert_series_rules)
            )
        end;

    .cr_monitor_series_id = ((.cr_monitor_series_id // {}) | convert_monitor_map)
    | .hidive_monitor_series_id = ((.hidive_monitor_series_id // {}) | convert_monitor_map)
' "$CONFIG_FILE" > "$temp_config_file"

mv "$temp_config_file" "$CONFIG_FILE"

echo "[migration:2.4.0] Updated cr_monitor_series_id and hidive_monitor_series_id"
echo "[migration:2.4.0] Migration complete"