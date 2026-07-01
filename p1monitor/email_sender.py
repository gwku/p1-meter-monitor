#!/usr/bin/env python3

import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


class EmailSender:

    def __init__(self):
        self.smtp_host = os.environ['SMTP_HOST']
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.environ['SMTP_USER']
        self.smtp_pass = os.environ['SMTP_PASS']
        self.smtp_from = os.getenv('SMTP_FROM', self.smtp_user)
        self.smtp_from_name = os.getenv('SMTP_FROM_NAME', 'P1 Meter Systeem')

        smtp_to_raw = os.getenv('P1_EMAIL_TO', '')
        self.smtp_to = [email.strip() for email in smtp_to_raw.split(',') if email.strip()]
        if not self.smtp_to:
            raise RuntimeError("P1_EMAIL_TO is empty or missing")

    def send_email(self, subject, html_content, csv_content=None, csv_filename=None):
        msg = MIMEMultipart('mixed')
        msg['From'] = f"{self.smtp_from_name} <{self.smtp_from}>"
        msg['To'] = ', '.join(self.smtp_to)
        msg['Subject'] = subject

        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)

        if csv_content and csv_filename:
            attachment = MIMEBase('text', 'csv')
            attachment.set_payload(csv_content.encode('utf-8'))
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename="{csv_filename}"')
            msg.attach(attachment)

        if self.smtp_port == 465:
            with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)

        recipient_count = len(self.smtp_to)
        recipients_str = ', '.join(self.smtp_to) if recipient_count <= 3 else f"{', '.join(self.smtp_to[:3])} + {recipient_count - 3} more"
        logger.info(f"✓ Email sent to {recipient_count} recipient(s): {recipients_str}")
        if csv_filename:
            logger.info(f"  - CSV attached: {csv_filename}")

