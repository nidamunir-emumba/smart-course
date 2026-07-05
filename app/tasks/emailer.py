"""Email delivery for notification tasks.

Two backends, selected by EMAIL_BACKEND:
  - "console": log the rendered email (dev default — works with no provider).
  - "smtp":    send through the configured SMTP server via stdlib smtplib.

Runs inside the synchronous Celery worker, so plain blocking I/O is fine here.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Deliver one email via the configured backend. Raises on SMTP failure
    so the calling Celery task can retry."""
    if settings.email_backend == "smtp":
        _send_smtp(to, subject, body)
    else:
        logger.info(
            "email (console backend) to=%s subject=%r\n%s", to, subject, body
        )


def _send_smtp(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
