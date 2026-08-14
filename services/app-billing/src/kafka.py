"""Kafka consumer — consumes user.create events and creates billing accounts."""

from __future__ import annotations

import asyncio
import json

from aiokafka import AIOKafkaConsumer
from opentelemetry import trace
from src.core.config import settings
from src.core.logger import log
from src.core.tracing import TRACER, kafka_extract_context, start_span
from src.crud import AccountCRUD

_consumer: AIOKafkaConsumer | None = None
_consumer_task: asyncio.Task[None] | None = None


async def _consume_loop(
    bootstrap_servers: str,
    topic: str,
    crud: AccountCRUD,
) -> None:
    """Internal consume loop — deserializes messages and delegates to AccountCRUD."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=settings.app_title,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    global _consumer
    _consumer = consumer

    await consumer.start()
    log.info("Kafka consumer started (bootstrap: %s, topic: %s)", bootstrap_servers, topic)

    try:
        async for msg in consumer:
            ctx = kafka_extract_context(msg.headers)
            with TRACER.start_as_current_span(
                "kafka.consume",
                context=ctx,
                kind=trace.SpanKind.CONSUMER,
                attributes={
                    "messaging.system": "kafka",
                    "messaging.destination": topic,
                    "messaging.destination_kind": "topic",
                    "messaging.operation": "process",
                    "messaging.kafka.consumer_group": settings.app_title,
                    "messaging.kafka.message_key": msg.key.decode("utf-8") if msg.key else None,
                    "messaging.kafka.partition": msg.partition,
                    "messaging.kafka.offset": msg.offset,
                },
            ):
                payload: dict[str, str] = msg.value
                username = payload.get("username")

                if not username:
                    log.warning("Skipping user.create message without username: %s", payload)
                    await consumer.commit()
                    continue

                try:
                    with start_span("billing.create_account_from_kafka", attributes={"billing.username": username}):
                        await crud.create_account(username)
                    await consumer.commit()
                    log.info("Created billing account: username=%s", username)
                except Exception:
                    log.exception("Failed to create billing account: username=%s", username)
                    continue  # do not commit offset on failure

    except asyncio.CancelledError:
        log.info("Kafka consumer loop cancelled")
        raise
    finally:
        await consumer.stop()
        log.info("Kafka consumer stopped")


async def start_consumer(crud: AccountCRUD) -> None:
    """Start the Kafka consumer as a background task (idempotent)."""
    global _consumer_task
    if _consumer_task is not None and not _consumer_task.done():
        log.warning("Kafka consumer already running — skipping duplicate start")
        return

    if not settings.kafka_bootstrap_servers:
        log.warning("KAFKA_BOOTSTRAP_SERVERS not configured — Kafka consumer disabled")
        return

    _consumer_task = asyncio.create_task(
        _consume_loop(settings.kafka_bootstrap_servers, settings.kafka_user_create_topic, crud)
    )
    log.info("Kafka consumer background task launched")


async def stop_consumer() -> None:
    """Gracefully stop the Kafka consumer (called on app shutdown)."""
    global _consumer_task
    if _consumer_task is not None and not _consumer_task.done():
        _consumer_task.cancel()
        try:
            await _consumer_task
        except asyncio.CancelledError:
            pass
        _consumer_task = None
        log.info("Kafka consumer task cancelled and awaited")
