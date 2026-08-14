from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from opentelemetry import trace
from src.core.config import settings
from src.core.logger import log
from src.core.tracing import TRACER, kafka_extract_context, start_span
from src.crud import UserCRUD
from src.schemes import UserUpdate

if TYPE_CHECKING:
    from src.kafka import KafkaClient


async def start_main_process(kafka_client: KafkaClient, crud: UserCRUD) -> None:
    await kafka_client.start()
    _consumer_task = asyncio.create_task(_consume_loop(kafka_client, crud))
    log.info("Kafka consumer background task launched")


async def _consume_loop(kafka_client: KafkaClient, crud: UserCRUD) -> None:
    try:
        async for msg in kafka_client.consumer:
            ctx = kafka_extract_context(msg.headers)
            with TRACER.start_as_current_span(
                "kafka.consume",
                context=ctx,
                kind=trace.SpanKind.CONSUMER,
                attributes={
                    "messaging.system": "kafka",
                    "messaging.destination": msg.topic,
                    "messaging.destination_kind": "topic",
                    "messaging.kafka.partition": msg.partition,
                    "messaging.kafka.message.offset": msg.offset,
                },
            ):
                payload: dict[str, str] = msg.value
                log.info(
                    "%s: Received Kafka message (%s %s:%s): payload=%s",
                    msg.key,
                    msg.topic,
                    msg.partition,
                    msg.offset,
                    payload,
                )

                if not isinstance(payload, dict):
                    log.error("%s: Message has incorrect body", msg.key)
                    continue

                try:
                    username: str | None = payload.get("username")
                    email: str | None = payload.get("email")

                    if not username or not email:
                        raise ValueError

                except ValueError:
                    log.error(
                        "%s: Skipping message without username/email: %s",
                        msg.key,
                        payload,
                    )
                    await kafka_client.send(msg, settings.kafka_user_create_topic_dlq)
                    await kafka_client.consumer.commit()
                    continue

                try:
                    with start_span(
                        "user.update_from_kafka", attributes={"user.username": username, "user.email": email}
                    ):
                        await crud.get_or_update_user(username, UserUpdate(email=email))
                    await kafka_client.consumer.commit()
                except Exception as err:
                    log.exception("%s: Failed to process user creation: %s", msg.key, err)
                    await kafka_client.send(msg, settings.kafka_user_create_topic_dlq)
                    await kafka_client.consumer.commit()
                    continue
    except asyncio.CancelledError as err:
        log.critical("Kafka consumer loop cancelled: %s", err)
        raise

    finally:
        await kafka_client.stop()
        log.critical("Kafka consumer/producer stopped")
