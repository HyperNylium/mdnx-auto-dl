
import subprocess
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








# import smtplib
# class Notification:
#     def __init__(self, email, password, smtp_server, smtp_port, smtp_tls=True, smtp_ssl=False):
#         self.email = email
#         self.password = password
#         self.smtp_server = smtp_server
#         self.smtp_port = smtp_port
#         self.smtp_tls = smtp_tls
#         self.smtp_ssl = smtp_ssl
    
#     def send_email(self, to, subject, body):
#         try:
#             server = smtplib.SMTP(self.smtp_server, self.smtp_port)
#             if self.smtp_tls:
#                 server.starttls()
#             if self.smtp_ssl:
#                 server.login(self.email, self.password)
#             server.sendmail(self.email, to, f"Subject: {subject}\n\n{body}")
#             server.quit()
#         except Exception as e:
#             logger.info(f"[Notification] Error sending email: {e}")
#             return False
#         return True