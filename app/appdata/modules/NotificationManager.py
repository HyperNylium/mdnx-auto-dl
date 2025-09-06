
import subprocess
import smtplib
from email.message import EmailMessage

# Custom imports
from .Vars import logger, config



class ntfy:
    def __init__(self):
        self.ntfy_script_path = config["app"]["NTFY_SCRIPT_PATH"]

    def notify(self, subject, message):
        try:
            logger.info(f"[Notification][ntfy] Sending ntfy notification...")
            subprocess.run([self.ntfy_script_path, subject, message], check=True)
        except Exception as e:
            logger.error(f"[Notification][ntfy] Error sending notification: {e}")
            return False
        return True

class SMTP:
    def __init__(self):
        self.SMTP_FROM = config["app"]["SMTP_FROM"]
        self.SMTP_TO = config["app"]["SMTP_TO"]
        self.SMTP_HOST = config["app"]["SMTP_HOST"]
        self.SMTP_USERNAME = config["app"]["SMTP_USERNAME"]
        self.SMTP_PASSWORD = config["app"]["SMTP_PASSWORD"]
        self.SMTP_PORT = config["app"]["SMTP_PORT"]
        self.SMTP_STARTTLS = config["app"]["SMTP_STARTTLS"]

    def notify(self, subject, message):
        try:
            logger.debug(f"[Notification][SMTP] Sending email notification to {self.SMTP_TO}...")
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
            logger.error(f"[Notification][SMTP] Error sending email: {e}")
            return False

        return True
