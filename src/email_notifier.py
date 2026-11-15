"""Email notification module for Inpol Monitor.

Provides email notifications as a fallback mechanism for when Telegram
notifications fail or as an alternative notification channel.
"""

import html
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

try:
    from src.localization import t as _t
    _USE_L10N = True
except ImportError:
    _USE_L10N = False
    def _t(key, default=None, language=None):
        return default or key

logger = logging.getLogger(__name__)


def t(key, default=None):
    """Translation wrapper that uses NOTIFICATION_LANGUAGE env var."""
    lang = os.getenv('NOTIFICATION_LANGUAGE', 'en')
    return _t(key, default, language=lang)


class EmailNotifier:
    """Email notification utility for case change alerts.

    Sends HTML and plain-text formatted emails when Telegram
    notifications fail or as an alternative channel.
    """

    def __init__(self, smtp_config: Dict[str, Any]):
        """Initialize email notifier with SMTP configuration.

        Args:
            smtp_config: Dictionary with SMTP settings:
                - host: SMTP server hostname
                - port: SMTP port (default 587)
                - username: SMTP authentication username
                - password: SMTP authentication password
                - from_addr: Sender email address
                - to_addr: Recipient email address
        """
        self.host = smtp_config.get("host", "")
        self.port = smtp_config.get("port", 587)
        self.username = smtp_config.get("username", "")
        self.password = smtp_config.get("password", "")
        self.from_addr = smtp_config.get("from_addr", "")
        self.to_addr = smtp_config.get("to_addr", "")

        self.enabled = bool(
            self.host and self.from_addr and self.to_addr
        )

    def send_change_notification(
        self,
        account_id: str,
        case_id: str,
        case_type: str,
        person_first: str,
        changes: List[Dict[str, Any]],
        status: str = ""
    ) -> bool:
        """Send email notification for case changes.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            case_type: Type of case
            person_first: First name of applicant
            changes: List of change dictionaries
            status: Case status code (optional)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled, skipping")
            return False

        if not self._validate_config():
            logger.error("Email configuration incomplete")
            return False

        subject = f"Inpol: {t('Dashboard.ActiveCases.Title', 'Changes')} {t('Cases.Signature', 'for case')} {case_id}"
        body = self._format_change_email(
            account_id, case_id, case_type, person_first, changes, status
        )

        return self._send_email(subject, body)

    def send_combined_notification(
        self,
        account_logins: List[str],
        cases: List[Any],
        html_body: str,
    ) -> bool:
        """Send combined email notification for multiple cases.

        Args:
            account_logins: List of account login emails
            cases: List of case info objects
            html_body: Pre-built HTML content (same as Telegram format)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled, skipping")
            return False

        if not self._validate_config():
            logger.error("Email configuration incomplete")
            return False

        total_changes = sum(c.total_changes for c in cases)
        subject = f"Inpol: {total_changes} changes in {len(cases)} cases"

        # Convert newlines to <br> for proper HTML rendering
        formatted_body = html_body.replace("\n", "<br>\n")

        # Wrap the Telegram-style HTML in email template
        full_html = f"""<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6;">
<div style="background-color: #f5f5f5; padding: 20px;">
<div style="background-color: white; padding: 20px; border-radius: 8px;">
{formatted_body}
</div>
<hr>
<p style="color: #666; font-size: 12px;">
Sent by Inpol Monitor<br>
Accounts: {", ".join(account_logins)}
</p>
</div>
</body>
</html>"""

        return self._send_email(subject, full_html)

    def send_error_notification(
        self,
        account_id: str,
        case_id: str,
        error_message: str,
        error_type: str,
    ) -> bool:
        """Send email notification for errors.

        Args:
            account_id: Account identifier
            case_id: Case identifier
            error_message: Error message
            error_type: Type of error (e.g., LOGIN_ERROR, SCRAPE_ERROR)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled, skipping")
            return False

        if not self._validate_config():
            logger.error("Email configuration incomplete")
            return False

        subject = f"Inpol Error: {error_type} for case {case_id}"
        body = self._format_error_email(
            account_id, case_id, error_message, error_type
        )

        return self._send_email(subject, body)

    def _validate_config(self) -> bool:
        """Validate that all required SMTP configuration is present."""
        return bool(
            self.host
            and self.username
            and self.password
            and self.from_addr
            and self.to_addr
        )

    def _format_change_email(
        self,
        account_id: str,
        case_id: str,
        case_type: str,
        person_first: str,
        changes: List[Dict[str, Any]],
        status: str = ""
    ) -> str:
        """Format email content for case changes."""
        from src.localization import t as _t
        status_label = _t(f'Cases.States.{status}', status) if status else ""
        
        html_content = f"""<html>
<body>
<h2>Inpol Case Update</h2>
<p><strong>Case ID:</strong> {html.escape(case_id)}</p>
<p><strong>Account:</strong> {html.escape(account_id)}</p>
<p><strong>Type:</strong> {html.escape(case_type)}</p>
<p><strong>Status:</strong> {html.escape(status)} - {html.escape(status_label)}</p>
<p><strong>Person:</strong> {html.escape(person_first)}</p>
<h3>Changes:</h3>
<ul>
"""
        for change in changes:
            change_type = html.escape(str(change.get("type", "unknown")))
            old_val = html.escape(str(change.get("old_value", "")))
            new_val = html.escape(str(change.get("new_value", "")))
            desc = html.escape(str(change.get("description", "")))
            html_content += f"<li><strong>{change_type}</strong>: {old_val} &rarr; {new_val}"
            if desc:
                html_content += f" ({desc})"
            html_content += "</li>"

        if not changes:
            html_content += "<li>No changes detected</li>"

        html_content += """</ul>
<p>---
Inpol Monitor</p>
</body>
</html>"""

        return html_content

    def _format_error_email(
        self,
        account_id: str,
        case_id: str,
        error_message: str,
        error_type: str,
    ) -> str:
        """Format email content for errors."""
        html_content = f"""<html>
<body>
<h2>Inpol Error Alert</h2>
<p><strong>Error Type:</strong> {html.escape(error_type)}</p>
<p><strong>Case ID:</strong> {html.escape(case_id)}</p>
<p><strong>Account:</strong> {html.escape(account_id)}</p>
<p><strong>Message:</strong> {html.escape(error_message)}</p>
<p>---
Inpol Monitor</p>
</body>
</html>"""

        return html_content

    def _send_email(self, subject: str, html_body: str) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_addr
            msg["To"] = self.to_addr

            text_part = MIMEText(html_body, "plain")
            html_part = MIMEText(html_body, "html")

            msg.attach(text_part)
            msg.attach(html_part)

            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.username, self.password)
            server.sendmail(self.from_addr, self.to_addr, msg.as_string())
            server.quit()

            logger.info(f"Email sent successfully: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False