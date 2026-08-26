from __future__ import annotations
import smtplib
from email.message import EmailMessage
from app.core.config import settings

class EmailService:
  async def send(
    self,
    *,
    recipient: str,
    subject: str,
    body: str,
  ) -> None:
    if not settings.email_enabled:
      return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = (
      f"{settings.smtp_from_name} "
      f"<{settings.smtp_from_email}>"
    )
    message["To"] = recipient

    message.set_content(body)

    if settings.smtp_use_tls:
      with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
      ) as smtp:
        smtp.starttls()
        smtp.login(
          settings.smtp_username,
          settings.smtp_password,
        )
        smtp.send_message(message)

    else:
      with smtplib.SMTP(
        settings.smtp_host,
        settings.smtp_port,
      ) as smtp:
        smtp.login(
          settings.smtp_username,
          settings.smtp_password,
        )
        smtp.send_message(message)