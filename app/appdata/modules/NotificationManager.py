import smtplib
import requests
from email.message import EmailMessage
from email.utils import formataddr

from .Globals import log_manager
from .Vars import config


def _send_grouped(send_func, action: str, series_name: str, item_blocks: list, max_size: int, count_bytes: bool) -> bool:

    count = len(item_blocks)
    item_word = "item" if count == 1 else "items"
    if action == "new":
        title = f"Added {count} {item_word} to {series_name}"
    else:
        title = f"Updated {count} {item_word} in {series_name}"

    def measure(text: str) -> int:
        if count_bytes:
            return len(text.encode("utf-8"))
        return len(text)

    separator = "\n\n"
    separator_size = measure(separator)

    bodies = []
    current_blocks = []
    current_size = 0
    for block in item_blocks:
        block_size = measure(block)
        added_size = block_size if not current_blocks else block_size + separator_size

        if current_blocks and current_size + added_size > max_size:
            bodies.append(separator.join(current_blocks))
            current_blocks = [block]
            current_size = block_size
        else:
            current_blocks.append(block)
            current_size += added_size

    if current_blocks:
        bodies.append(separator.join(current_blocks))

    total = len(bodies)
    all_ok = True
    for index, body in enumerate(bodies, start=1):
        if total == 1:
            chunk_title = title
        else:
            chunk_title = f"{title} (part {index}/{total})"

        if not send_func(chunk_title, body):
            all_ok = False

    return all_ok


class SMTP:
    send_per_series = False

    def __init__(self):
        self.SMTP_FROM = config.app.smtp_from
        self.SMTP_TO = config.app.smtp_to
        self.SMTP_HOST = config.app.smtp_host
        self.SMTP_USERNAME = config.app.smtp_username
        self.SMTP_PASSWORD = config.app.smtp_password
        self.SMTP_PORT = config.app.smtp_port
        self.SMTP_STARTTLS = config.app.smtp_starttls

    def notify(self, subject: str, message: str):
        """Send email notification using SMTP."""
        try:
            log_manager.debug(f"Sending email notification to {self.SMTP_TO}...")
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = formataddr(("mdnx-auto-dl", self.SMTP_FROM))
            msg["To"] = self.SMTP_TO
            msg.set_content(message, charset="utf-8")

            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT, timeout=30) as server:
                if self.SMTP_STARTTLS:
                    server.starttls()
                server.login(self.SMTP_USERNAME, self.SMTP_PASSWORD)
                server.send_message(msg)

        except Exception as e:
            log_manager.error(f"Failed to send email: {e}", exc_info=e)
            return False

        return True


class ntfy:
    # ntfy rejects messages larger than ~4096 bytes so keep bodies under that
    MAX_BODY = 3900
    COUNT_BYTES = True
    send_per_series = True

    def __init__(self):
        self.url = config.app.ntfy_url
        self.token = config.app.ntfy_token
        self.username = config.app.ntfy_username
        self.password = config.app.ntfy_password
        self.priority = config.app.ntfy_priority
        self.tags = config.app.ntfy_tags

    def notify_series(self, action: str, series_name: str, item_blocks: list) -> bool:
        return _send_grouped(self._send, action, series_name, item_blocks, self.MAX_BODY, self.COUNT_BYTES)

    def _send(self, subject: str, message: str):
        """Send one message to an ntfy topic."""
        try:
            log_manager.info("Sending ntfy notification...")

            headers = {"Title": subject}
            if self.priority:
                headers["Priority"] = self.priority

            # ntfy wants tags as one comma separated list in a single header
            if self.tags:
                headers["Tags"] = ",".join(self.tags)

            # ntfy supports both token-based and basic auth, but not at the same time.
            # We prefer token auth if a token is provided.
            auth = None
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            elif self.username:
                auth = (self.username, self.password)

            response = requests.post(
                self.url,
                data=message.encode("utf-8"),
                headers=headers,
                auth=auth,
                timeout=30
            )
            response.raise_for_status()

        except Exception as e:
            log_manager.error(f"Failed to send ntfy notification: {e}", exc_info=e)
            return False

        return True


class Gotify:
    # gotify has no size limit, so it almost never needs to split (from my testing)
    MAX_BODY = 100000
    COUNT_BYTES = False
    send_per_series = True

    def __init__(self):
        self.url = config.app.gotify_url
        self.token = config.app.gotify_token
        self.priority = config.app.gotify_priority

    def notify_series(self, action: str, series_name: str, item_blocks: list) -> bool:
        return _send_grouped(self._send, action, series_name, item_blocks, self.MAX_BODY, self.COUNT_BYTES)

    def _send(self, subject: str, message: str):
        """Send one message to a gotify server."""
        try:
            log_manager.info("Sending gotify notification...")

            base_url = self.url.rstrip("/")
            payload = {
                "title": subject,
                "message": message,
                "priority": self.priority
            }

            response = requests.post(
                f"{base_url}/message",
                headers={"X-Gotify-Key": self.token},
                json=payload,
                timeout=30
            )
            response.raise_for_status()

        except Exception as e:
            log_manager.error(f"Failed to send gotify notification: {e}", exc_info=e)
            return False

        return True


class Discord:
    # discord caps embed titles at 256 chars and descriptions at 4096
    TITLE_LIMIT = 256
    DESCRIPTION_LIMIT = 4096
    MAX_BODY = 4000
    COUNT_BYTES = False
    send_per_series = True

    def __init__(self):
        self.webhook_url = config.app.discord_webhook_url

    def notify_series(self, action: str, series_name: str, item_blocks: list) -> bool:
        return _send_grouped(self._send, action, series_name, item_blocks, self.MAX_BODY, self.COUNT_BYTES)

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text

        suffix = "... (truncated)"
        return text[:limit - len(suffix)] + suffix

    def _send(self, subject: str, message: str):
        """Send one message to a Discord channel using a webhook embed."""
        try:
            log_manager.info("Sending Discord notification...")

            embed = {
                "title": self._truncate(subject, self.TITLE_LIMIT),
                "description": self._truncate(message, self.DESCRIPTION_LIMIT)
            }

            response = requests.post(
                self.webhook_url,
                json={"embeds": [embed]},
                timeout=30
            )
            response.raise_for_status()

        except Exception as e:
            log_manager.error(f"Failed to send Discord notification: {e}", exc_info=e)
            return False

        return True
