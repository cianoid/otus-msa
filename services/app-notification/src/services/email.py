"""EmailService — loads, renders, and persists notification messages."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from core.enums import MessageStatus
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from src.core.const import NO_SUBJECT
from src.core.enums import MessageTypes
from src.core.logger import log
from src.crud import NotificationCRUD


class EmailService:
    """Loads an HTML template by *message_type*, renders it with the provided
    keyword arguments, and persists the result via *NotificationCRUD*.

    Usage::

        svc = EmailService(Path("src/templates"), notification_crud)
        await svc.send("ORDER_SUCCESS", username="cianoid", email="cianoid@ya.ru")
    """

    def __init__(self, template_dir: Path, crud: NotificationCRUD) -> None:
        env = Environment(loader=FileSystemLoader(str(template_dir)))
        self._env = env
        self._crud = crud

    async def _send_email(self, email: str, subject: str, body: str) -> bool:
        return True

    async def send(
        self, notification_id: UUID, message_type: MessageTypes, email: str, username: str, **kwargs
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

        body: str = template.render(**kwargs)
        subject: str = kwargs.get("subject", NO_SUBJECT)
        await self._crud.update_message_with_data(notification_id, subject=subject, body=body)

        if await self._send_email(email, subject, body):
            await self._crud.update_message_success(notification_id)
            log.info("%s: Email sent", notification_id)
            return

        await self._crud.update_message_error(notification_id)
        log.error("%s: Email not sent", notification_id)
        return
