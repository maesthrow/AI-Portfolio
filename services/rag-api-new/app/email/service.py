"""SMTP email service for sending CV/resume."""
from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.header import Header
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path

from .templates import CV_EMAIL_SUBJECT, cv_email_body_html, cv_email_body_plain

logger = logging.getLogger(__name__)


@dataclass
class EmailResult:
    """Result of an email sending attempt."""

    success: bool
    message: str
    error: str | None = None


class EmailService:
    """SMTP-based email service for sending CV.

    Synchronous — call via ``asyncio.to_thread()`` in async context.
    Uses the same threading pattern as ``rag_tool.py``.
    """

    def __init__(self, settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """Return True when SMTP credentials are configured."""
        s = self._settings
        return bool(s.smtp_host and s.smtp_user and s.smtp_password and s.smtp_from_email)

    def send_cv(self, to_email: str) -> EmailResult:
        """Send CV PDF to *to_email*.

        This is a **synchronous** method — wrap in ``asyncio.to_thread()``.

        Returns:
            EmailResult with user-friendly message.
        """
        cv_path = Path(self._settings.cv_file_path)

        if not cv_path.is_file():
            logger.error("CV file not found: %s", cv_path)
            return EmailResult(
                success=False,
                message="Сервис отправки CV временно недоступен. Попробуйте позже.",
                error=f"CV file not found: {cv_path}",
            )

        try:
            msg = self._build_message(to_email, cv_path)
            self._send_smtp(msg)
            logger.info("CV sent successfully to %s", to_email)
            return EmailResult(
                success=True,
                message=f"Резюме успешно отправлено на {to_email}!",
            )
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("SMTP auth failed: %s", exc)
            return EmailResult(
                success=False,
                message="Не удалось отправить резюме. Попробуйте позже или свяжитесь напрямую через контакты.",
                error=f"SMTP auth error: {exc}",
            )
        except smtplib.SMTPException as exc:
            logger.error("SMTP error sending CV to %s: %s", to_email, exc)
            return EmailResult(
                success=False,
                message="Не удалось отправить резюме. Попробуйте позже или свяжитесь напрямую через контакты.",
                error=f"SMTP error: {exc}",
            )
        except Exception as exc:
            logger.error("Unexpected error sending CV to %s: %s", to_email, exc, exc_info=True)
            return EmailResult(
                success=False,
                message="Не удалось отправить резюме. Попробуйте позже или свяжитесь напрямую через контакты.",
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_message(self, to_email: str, cv_path: Path) -> MIMEMultipart:
        """Build multipart MIME message with HTML body + PDF attachment."""
        s = self._settings

        msg = MIMEMultipart("mixed")
        msg["Subject"] = CV_EMAIL_SUBJECT
        msg["From"] = formataddr((str(Header(s.smtp_from_name, "utf-8")), s.smtp_from_email))
        msg["To"] = to_email

        # Build site URL from domain setting
        site_url = f"https://{s.domain}" if s.domain else ""

        # Body: HTML with plain-text fallback
        body = MIMEMultipart("alternative")
        body.attach(MIMEText(cv_email_body_plain(site_url), "plain", "utf-8"))
        body.attach(MIMEText(cv_email_body_html(site_url), "html", "utf-8"))
        msg.attach(body)

        # Attachment: CV PDF
        pdf_data = cv_path.read_bytes()
        attachment = MIMEApplication(pdf_data, _subtype="pdf")
        attach_name = s.cv_attachment_name or cv_path.name
        attachment.add_header(
            "Content-Disposition",
            "attachment",
            filename=attach_name,
        )
        msg.attach(attachment)

        return msg

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Connect to SMTP server and send the message."""
        s = self._settings

        if s.smtp_use_tls:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30)
            server.ehlo()

        try:
            server.login(s.smtp_user, s.smtp_password)
            server.send_message(msg)
        finally:
            server.quit()
