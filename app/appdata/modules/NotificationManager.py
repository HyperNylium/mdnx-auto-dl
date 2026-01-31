import smtplib
import subprocess
from email.message import EmailMessage

from .Globals import log_manager
from .Vars import config


class ntfy:
    def __init__(self):
        self.ntfy_script_path = config.app.ntfy_script_path

    def notify(self, subject, message):
        """Send notification using ntfy script."""
        try:
            log_manager.info("Sending ntfy notification...")
            subprocess.run([self.ntfy_script_path, subject, message], check=True)
        except Exception as e:
            log_manager.error(f"Error sending notification: {e}")
            return False
        return True


class SMTP:
    def __init__(self):
        self.SMTP_FROM = config.app.smtp_from
        self.SMTP_TO = config.app.smtp_to
        self.SMTP_HOST = config.app.smtp_host
        self.SMTP_USERNAME = config.app.smtp_username
        self.SMTP_PASSWORD = config.app.smtp_password
        self.SMTP_PORT = config.app.smtp_port
        self.SMTP_STARTTLS = config.app.smtp_starttls

    def notify(self, subject, message):
        """Send email notification using SMTP."""
        try:
            log_manager.debug(f"Sending email notification to {self.SMTP_TO}...")
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.SMTP_FROM
            msg["To"] = self.SMTP_TO
            msg.set_content(message, charset="utf-8")

            with smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT) as server:
                if self.SMTP_STARTTLS:
                    server.starttls()
                server.login(self.SMTP_USERNAME, self.SMTP_PASSWORD)
                server.send_message(msg)

        except Exception as e:
            log_manager.error(f"Error sending email: {e}")
            return False

        return True
