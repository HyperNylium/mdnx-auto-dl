# Send SMTP notification when new episode is downloaded for a series
# This is a quick draft of what i am thinking and needs improvement
# NOT PROD READY!!!

import smtplib
from .Vars import logger



class Notification:
    def __init__(self, email, password, smtp_server, smtp_port, smtp_tls=True, smtp_ssl=False):
        self.email = email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_tls = smtp_tls
        self.smtp_ssl = smtp_ssl
    
    def send_email(self, to, subject, body):
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            if self.smtp_tls:
                server.starttls()
            if self.smtp_ssl:
                server.login(self.email, self.password)
            server.sendmail(self.email, to, f"Subject: {subject}\n\n{body}")
            server.quit()
        except Exception as e:
            logger.info(f"[Notification] Error sending email: {e}")
            return False
        return True