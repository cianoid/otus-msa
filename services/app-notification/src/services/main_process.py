from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.core.config import settings
from src.core.enums import MessageTypes
from src.core.logger import log

if TYPE_CHECKING:
    from src.kafka import KafkaClient
    from src.services.email import EmailService


async def start_main_process(kafka_client: KafkaClient, email_client: EmailService) -> None:
    await kafka_client.start()
    _consumer_task = asyncio.create_task(_consume_loop(kafka_client, email_client))
    log.info("Kafka consumer background task launched")


async def _consume_loop(kafka_client: KafkaClient, email_client: EmailService) -> None:
    """Internal consume loop — deserializes messages and delegates to EmailService."""

    try:
        async for msg in kafka_client.consumer:
            payload: dict[str, dict] = msg.value
            log.info(
                "%s: Received Kafka message (%s %s:%s): payload=%s",
                msg.key,
                msg.topic,
                msg.partition,
                msg.offset,
                payload,
            )

            if not isinstance(payload, dict) or "meta" not in payload:
                log.error("%s: Message has incorrect body", msg.key)
                continue

            try:
                meta = payload.get("meta", {})
                message_type: MessageTypes = MessageTypes(meta.get("message_type"))
                username: str | None = meta.get("username")
                email: str | None = meta.get("email")

                if not username or not email:
                    raise ValueError

            except ValueError:
                log.error(
                    "%s: Skipping message without message_type/username/email: %s",
                    msg.key,
                    payload,
                )
                await kafka_client.send(msg, settings.kafka_send_email_topic_dlq)
                await kafka_client.consumer.commit()
                continue

            try:
                await email_client.send(
                    notification_id=msg.key,
                    message_type=message_type,
                    email=email,
                    username=username,
                    data=payload.get("data", {}),
                )
                await kafka_client.consumer.commit()
            except Exception as err:
                log.exception(
                    "%s: Failed to process notification with type=%s: %s",
                    msg.key,
                    message_type,
                    err,
                )
                continue

    except asyncio.CancelledError as err:
        log.critical("Kafka consumer loop cancelled: %s", err)
        raise

    finally:
        await kafka_client.stop()
        log.critical("Kafka consumer/producer stopped")
