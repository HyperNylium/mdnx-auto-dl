# How-to: Set up notifications

mdnx-auto-dl can tell you when it adds or updates episodes. It supports 4 providers: **SMTP** email, **ntfy**, **Gotify**, and **Discord** (webhook).

Each provider has its own `*_ENABLED` flag and they are independent, so you can turn on **as many as you want at the same time**. Every enabled provider receives each notification. If none are enabled, no notifications are sent.

> [!NOTE]
> SMTP sends one combined summary message per loop pass. The push providers (ntfy, Gotify, Discord) send one message per series and automatically split long messages to stay within each provider's size limit.

If a provider is enabled but a required key is empty, the app exits on startup with a critical log line telling you what is missing.

All keys below live in the `app` section of your config file.

---

## SMTP email

Set [`SMTP_ENABLED`](../config-options.md#SMTP_ENABLED) to `true` and fill in the rest of the [`SMTP_*`](../config-options.md#SMTP_FROM) keys.

JSON:
```json
"app": {
    "SMTP_ENABLED": true,
    "SMTP_FROM": "who we sending as?",
    "SMTP_TO": "who we sending to?",
    "SMTP_HOST": "smtp.gmail.com, or whatever your email provider is",
    "SMTP_USERNAME": "your username. For gmail, this is your email address",
    "SMTP_PASSWORD": "your password. For gmail, this is your app password",
    "SMTP_PORT": 587,
    "SMTP_STARTTLS": true
}
```
YAML:
```yaml
app:
    SMTP_ENABLED: true
    SMTP_FROM: "who we sending as?"
    SMTP_TO: "who we sending to?"
    SMTP_HOST: "smtp.gmail.com, or whatever your email provider is"
    SMTP_USERNAME: "your username. For gmail, this is your email address"
    SMTP_PASSWORD: "your password. For gmail, this is your app password"
    SMTP_PORT: 587
    SMTP_STARTTLS: true
```

[`SMTP_TO`](../config-options.md#SMTP_TO) can be a single address or a list. See its reference entry for both formats.

**Keys:** [`SMTP_ENABLED`](../config-options.md#SMTP_ENABLED) [`SMTP_FROM`](../config-options.md#SMTP_FROM) [`SMTP_TO`](../config-options.md#SMTP_TO) [`SMTP_HOST`](../config-options.md#SMTP_HOST) [`SMTP_USERNAME`](../config-options.md#SMTP_USERNAME) [`SMTP_PASSWORD`](../config-options.md#SMTP_PASSWORD) [`SMTP_PORT`](../config-options.md#SMTP_PORT) [`SMTP_STARTTLS`](../config-options.md#SMTP_STARTTLS)

---

## ntfy

Set [`NTFY_ENABLED`](../config-options.md#NTFY_ENABLED) to `true` and point [`NTFY_URL`](../config-options.md#NTFY_URL) at your topic. Auth, priority, and tags are optional.

Minimal (public topic):
```json
"app": {
    "NTFY_ENABLED": true,
    "NTFY_URL": "https://ntfy.sh/my-topic"
}
```

Full example (protected topic with token auth, priority, and tags):
```json
"app": {
    "NTFY_ENABLED": true,
    "NTFY_URL": "https://ntfy.example.com/my-topic",
    "NTFY_TOKEN": "tk_your_ntfy_token",
    "NTFY_PRIORITY": "high",
    "NTFY_TAGS": ["white_check_mark", "tv"]
}
```
YAML:
```yaml
app:
    NTFY_ENABLED: true
    NTFY_URL: "https://ntfy.example.com/my-topic"
    NTFY_TOKEN: "tk_your_ntfy_token"
    NTFY_PRIORITY: "high"
    NTFY_TAGS:
        - "white_check_mark"
        - "tv"
```

For a private topic use **either** a token ([`NTFY_TOKEN`](../config-options.md#NTFY_TOKEN)) **or** basic auth ([`NTFY_USERNAME`](../config-options.md#NTFY_USERNAME) + [`NTFY_PASSWORD`](../config-options.md#NTFY_PASSWORD)), not both. If a token is set, it wins.

**Keys:** [`NTFY_ENABLED`](../config-options.md#NTFY_ENABLED) [`NTFY_URL`](../config-options.md#NTFY_URL) [`NTFY_TOKEN`](../config-options.md#NTFY_TOKEN) [`NTFY_USERNAME`](../config-options.md#NTFY_USERNAME) [`NTFY_PASSWORD`](../config-options.md#NTFY_PASSWORD) [`NTFY_PRIORITY`](../config-options.md#NTFY_PRIORITY) [`NTFY_TAGS`](../config-options.md#NTFY_TAGS)

---

## Gotify

Set [`GOTIFY_ENABLED`](../config-options.md#GOTIFY_ENABLED) to `true`, then provide your server URL and an application token.

JSON:
```json
"app": {
    "GOTIFY_ENABLED": true,
    "GOTIFY_URL": "https://gotify.example.com",
    "GOTIFY_TOKEN": "your_gotify_app_token",
    "GOTIFY_PRIORITY": 5
}
```
YAML:
```yaml
app:
    GOTIFY_ENABLED: true
    GOTIFY_URL: "https://gotify.example.com"
    GOTIFY_TOKEN: "your_gotify_app_token"
    GOTIFY_PRIORITY: 5
```

Use the base URL of your Gotify server (no `/message` suffix). The app appends `/message` itself. Create the token in Gotify under **Apps**.

**Keys:** [`GOTIFY_ENABLED`](../config-options.md#GOTIFY_ENABLED) [`GOTIFY_URL`](../config-options.md#GOTIFY_URL) [`GOTIFY_TOKEN`](../config-options.md#GOTIFY_TOKEN) [`GOTIFY_PRIORITY`](../config-options.md#GOTIFY_PRIORITY)

---

## Discord

Create a webhook in Discord (**Server Settings > Integrations > Webhooks**), set [`DISCORD_ENABLED`](../config-options.md#DISCORD_ENABLED) to `true`, and paste the webhook URL.

JSON:
```json
"app": {
    "DISCORD_ENABLED": true,
    "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/123456789/your-webhook-token"
}
```
YAML:
```yaml
app:
    DISCORD_ENABLED: true
    DISCORD_WEBHOOK_URL: "https://discord.com/api/webhooks/123456789/your-webhook-token"
```

Notifications are posted as embeds. If Discord rate-limits the request, the app waits and retries automatically.

**Keys:** [`DISCORD_ENABLED`](../config-options.md#DISCORD_ENABLED) [`DISCORD_WEBHOOK_URL`](../config-options.md#DISCORD_WEBHOOK_URL)
