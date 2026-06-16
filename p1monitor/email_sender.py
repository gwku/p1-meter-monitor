#!/usr/bin/env python3
"""
Email Sender
Handles SMTP email sending with attachments
"""

import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

logger = logging.getLogger(__name__)


class EmailSender:
    """Sends emails via SMTP"""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.smtp_from = os.getenv('SMTP_FROM', self.smtp_user)
        self.smtp_from_name = os.getenv('SMTP_FROM_NAME', 'P1 Meter Systeem')
        
        # Support multiple recipients (comma-separated)
        smtp_to_raw = os.getenv('P1_EMAIL_TO', '')
        self.smtp_to = [email.strip() for email in smtp_to_raw.split(',') if email.strip()]
        
        self.smtp_tls = os.getenv('SMTP_TLS', 'yes').lower() == 'yes'
    
    def send_email(self, subject, html_content, csv_content=None, csv_filename=None):
        """Send email with HTML content and optional CSV attachment"""
        
        if not all([self.smtp_host, self.smtp_user, self.smtp_pass]) or not self.smtp_to:
            logger.error("SMTP not configured - skipping email")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart('mixed')
            msg['From'] = f"{self.smtp_from_name} <{self.smtp_from}>"
            msg['To'] = ', '.join(self.smtp_to)  # Join multiple recipients
            msg['Subject'] = subject
            
            # Add HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add CSV attachment if provided
            if csv_content and csv_filename:
                attachment = MIMEBase('text', 'csv')
                attachment.set_payload(csv_content.encode('utf-8'))
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', f'attachment; filename="{csv_filename}"')
                msg.attach(attachment)
            
            # Send email
            if self.smtp_tls and self.smtp_port != 465:
                # STARTTLS
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            else:
                # SSL or no encryption
                smtp_class = smtplib.SMTP_SSL if self.smtp_port == 465 else smtplib.SMTP
                with smtp_class(self.smtp_host, self.smtp_port, timeout=30) as server:
                    if self.smtp_port != 465:
                        server.ehlo()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.send_message(msg)
            
            recipient_count = len(self.smtp_to)
            recipients_str = ', '.join(self.smtp_to) if recipient_count <= 3 else f"{', '.join(self.smtp_to[:3])} + {recipient_count - 3} more"
            logger.info(f"✓ Email sent to {recipient_count} recipient(s): {recipients_str}")
            if csv_filename:
                logger.info(f"  - CSV attached: {csv_filename}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Email sending failed: {e}")
            return False

