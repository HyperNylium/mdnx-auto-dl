import time
import smtplib
import requests
from email.message import EmailMessage
from email.utils import formataddr

from .Globals import log_manager, stop_event
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
        self.error_attempts = 5   # tries on connection or 5xx errors before giving up
        self.max_rate_wait = 60   # cap in seconds for one rate limit wait
        self.min_rate_wait = 1    # floor in seconds so we never retry too fast
        self.max_429_total = 600  # cap in seconds for total rate limit waiting on one message

    def notify_series(self, action: str, series_name: str, item_blocks: list) -> bool:
        return _send_grouped(self._send, action, series_name, item_blocks, self.MAX_BODY, self.COUNT_BYTES)

    def _truncate(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text

        suffix = "... (truncated)"
        return text[:limit - len(suffix)] + suffix

    def _sleep(self, seconds: float) -> bool:
        """Sleep for the given seconds but wake up early if the app is shutting down."""

        end = time.time() + seconds
        while time.time() < end:
            if stop_event.is_set():
                return True
            time.sleep(max(0, min(1, end - time.time())))

        return stop_event.is_set()

    def _retry_after(self, response: requests.Response) -> float:
        """Read how many seconds Discord wants us to wait before trying again."""

        # the json body has the real wait time from my testing
        try:
            wait = float(response.json().get("retry_after"))
        except Exception:
            wait = self.max_rate_wait

        return max(self.min_rate_wait, min(wait, self.max_rate_wait))  # clamp to our min/max so we don't wait too long or too short

    def _cooldown(self, response: requests.Response) -> bool:
        """If we used up the rate limit bucket, wait the time Discord tells us to before sending another message."""

        if response.headers.get("X-RateLimit-Remaining") != "0":
            return False

        try:
            reset_after = float(response.headers.get("X-RateLimit-Reset-After"))
        except (TypeError, ValueError):
            return False

        reset_after = min(reset_after, self.max_rate_wait)
        if reset_after <= 0:
            return False

        log_manager.debug(f"Discord rate limit bucket used up. Cooling down for {reset_after}s before next send.")
        return self._sleep(reset_after)

    def _send(self, subject: str, message: str):
        """Send one message to a Discord channel using a webhook embed."""

        embed = {
            "title": self._truncate(subject, self.TITLE_LIMIT),
            "description": self._truncate(message, self.DESCRIPTION_LIMIT)
        }
        payload = {"embeds": [embed]}

        error_attempt = 0
        total_rate_wait = 0.0
        while True:
            if stop_event.is_set():
                log_manager.info("Shutdown requested. Skipping Discord notification.")
                return False

            try:
                log_manager.info("Sending Discord notification...")
                response = requests.post(self.webhook_url, json=payload, timeout=30)
            except requests.RequestException as network_error:
                error_attempt += 1
                if error_attempt >= self.error_attempts:
                    log_manager.error(f"Failed to send Discord notification after {error_attempt} tries: {network_error}", exc_info=network_error)
                    return False

                wait = min(30, 2 ** error_attempt)  # exponential backoff capped at 30s
                log_manager.warning(f"Discord request failed ({network_error}). Retrying in {wait}s...")
                if self._sleep(wait):
                    return False
                continue

            # discord is telling us to slow down so we slow TF down.
            if response.status_code == 429:
                wait = self._retry_after(response)
                total_rate_wait += wait
                if total_rate_wait > self.max_429_total:
                    log_manager.error(f"Discord kept rate limiting us past {self.max_429_total}s. Giving up on this message.")
                    return False

                log_manager.warning(f"Discord rate limited us. Waiting {wait}s before retry...")
                if self._sleep(wait):
                    return False
                continue

            # a 5xx is a server side problem. back off a few times then give up.
            if response.status_code >= 500:
                error_attempt += 1
                if error_attempt >= self.error_attempts:
                    log_manager.error(f"Discord returned {response.status_code} after {error_attempt} tries. Giving up on this message.")
                    return False

                wait = min(30, 2 ** error_attempt)  # exponential backoff capped at 30s
                log_manager.warning(f"Discord returned {response.status_code}. Retrying in {wait}s...")
                if self._sleep(wait):
                    return False
                continue

            try:
                response.raise_for_status()
            except Exception as bad_status:
                log_manager.error(f"Failed to send Discord notification: {bad_status}", exc_info=bad_status)
                return False

            self._cooldown(response)
            return True
