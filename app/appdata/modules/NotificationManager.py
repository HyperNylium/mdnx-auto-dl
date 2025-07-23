
import subprocess
import smtplib

# Custom imports
from .Vars import logger, config



class ntfy:
    def __init__(self):
        self.ntfy_script_path = config["app"]["NTFY_SCRIPT_PATH"]

    def notify(self, message):
        try:
            logger.info(f"[Notification][ntfy] Sending notification: {message}")
            subprocess.run([self.ntfy_script_path, message], check=True)
        except Exception as e:
            logger.info(f"[Notification][ntfy] Error sending notification: {e}")
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
        self.SMTP_TLS = config["app"]["SMTP_TLS"]

    def notify(self, body):
        try:
            print(f"[Notification][SMTP] Sending email notification to {self.SMTP_TO}...")
            server = smtplib.SMTP(self.SMTP_HOST, self.SMTP_PORT)
            if self.SMTP_TLS:
                server.starttls()
            server.login(self.SMTP_USERNAME, self.SMTP_PASSWORD)
            server.sendmail(self.SMTP_FROM, self.SMTP_TO, f"Subject: New episode downloaded!\n\n{body}")
            server.quit()
        except Exception as e:
            print(f"[Notification][SMTP] Error sending email: {e}")
            return False
        return True