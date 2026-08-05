"""EmailService — loads, renders, persists, and sends notification messages via SMTP."""

from __future__ import annotations

import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from uuid import UUID

from aiosmtplib import SMTP, SMTPException
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from src.core.config import settings
from src.core.enums import MessageStatus, MessageSubjects, MessageTypes
from src.core.logger import log
from src.crud import NotificationCRUD


class EmailService:
    """Loads an HTML template by *message_type*, renders it with the provided
    keyword arguments, persists the result via *NotificationCRUD*, and sends
    it through the configured SMTP server.

    Usage::

        svc = EmailService(Path("src/templates"), notification_crud)
        await svc.send("ORDER_SUCCESS", username="cianoid", email="cianoid@ya.ru")
    """

    def __init__(self, template_dir: Path, crud: NotificationCRUD) -> None:
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        self._env = env
        self._crud = crud

    def _build_message(self, to_email: str, subject: str, body: str) -> MIMEMultipart:
        """Build a multipart/alternative email message with text and HTML parts."""
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.smtp_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))
        return msg

    async def _send_email(self, email: str, subject: str, body: str) -> bool:
        """Send an email via the configured SMTP server.

        Returns True on success, False on failure.
        """
        for attempt in range(3):
            smtp = SMTP(hostname=settings.smtp_host, port=settings.smtp_port, use_tls=settings.smtp_use_tls)
            try:
                await smtp.connect()
                if settings.smtp_user:
                    await smtp.login(settings.smtp_user, settings.smtp_password)
                message = self._build_message(email, subject, body)
                await smtp.send_message(message)
                log.info("SMTP: message sent to %s (subject=%r)", email, subject)
                return True
            except SMTPException as err:
                log.error("SMTP: failed to send to %s (attempt %s): %s", email, attempt + 1, err)
            except Exception as err:
                log.exception("SMTP: unexpected error sending to %s (attempt %s): %s", email, attempt + 1, err)
            finally:
                try:
                    await smtp.quit()
                except Exception:
                    pass
            if attempt < 2:
                await asyncio.sleep(1)

        log.error("SMTP: giving up sending to %s after 3 attempts", email)
        return False

    async def send(
        self, notification_id: UUID, message_type: MessageTypes, email: str, username: str, data: dict
    ) -> None:
        """Render the ``<message_type>.html`` template with *kwargs* and persist
        the result.  *email* is required in *kwargs* and is popped before
        rendering so it remains the recipient, not a template variable."""

        item = await self._crud.get_one(notification_id)

        if item is not None:
            if item.status == MessageStatus.READY_TO_SEND:
                log.warning("%s: Something strange with notification. Status is %s", notification_id, item.status)
                return
            if item.status == MessageStatus.ERROR:
                log.warning(
                    "%s: Probably we should resend message, but we don't. Status is %s", notification_id, item.status
                )
                return
            if item.status == MessageStatus.SENT:
                return

        await self._crud.add_new_message(
            notification_id=notification_id, username=username, email=email, message_type=message_type
        )

        template_name = f"{message_type}.html"
        try:
            template = self._env.get_template(template_name)
        except TemplateNotFound:
            log.warning("%s: Template not found: %s — skipping", notification_id, template_name)
            await self._crud.update_message_error(notification_id)
            return

        subject = MessageSubjects[message_type].value
        data.update({"username": username, "email": email, "subject": subject})
        body: str = template.render(**data)
        await self._crud.update_message_with_data(notification_id, subject=subject, body=body)

        if await self._send_email(email, subject, body):
            await self._crud.update_message_success(notification_id)
            log.info("%s: Email sent", notification_id)
            return

        await self._crud.update_message_error(notification_id)
        log.error("%s: Email not sent", notification_id)
        return
