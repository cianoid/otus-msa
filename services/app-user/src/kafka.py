"""Kafka consumer — consumes user.create events and upserts into the local DB."""

from __future__ import annotations

import asyncio
import json

from aiokafka import AIOKafkaConsumer
from src.core.config import KAFKA_BOOTSTRAP_SERVERS, KAFKA_USER_CREATE_TOPIC, TITLE
from src.core.logger import log
from src.crud import UserCRUD
from src.schemes import UserUpdate

_consumer: AIOKafkaConsumer | None = None
_consumer_task: asyncio.Task[None] | None = None


async def _consume_loop(
    bootstrap_servers: str,
    topic: str,
    crud: UserCRUD,
) -> None:
    """Internal consume loop — deserializes messages and delegates upsert to UserCRUD."""
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=TITLE,
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    global _consumer
    _consumer = consumer

    await consumer.start()
    log.info("Kafka consumer started (bootstrap: %s, topic: %s)", bootstrap_servers, topic)

    try:
        async for msg in consumer:
            payload: dict[str, str] = msg.value
            username = payload.get("username")
            email = payload.get("email")

            if not username:
                log.warning("Skipping user.create message without username: %s", payload)
                continue

            try:
                await crud.get_or_update_user(username, UserUpdate(email=email))
                await consumer.commit()
                log.info("Upserted user: username=%s", username)
            except Exception:
                log.exception("Failed to upsert user: username=%s", username)
                continue  # do not commit offset on failure

    except asyncio.CancelledError:
        log.info("Kafka consumer loop cancelled")
        raise
    finally:
        await consumer.stop()
        log.info("Kafka consumer stopped")


async def start_consumer(crud: UserCRUD) -> None:
    """Start the Kafka consumer as a background task (idempotent)."""
    global _consumer_task
    if _consumer_task is not None and not _consumer_task.done():
        log.warning("Kafka consumer already running — skipping duplicate start")
        return

    if not KAFKA_BOOTSTRAP_SERVERS:
        log.warning("KAFKA_BOOTSTRAP_SERVERS not configured — Kafka consumer disabled")
        return

    _consumer_task = asyncio.create_task(_consume_loop(KAFKA_BOOTSTRAP_SERVERS, KAFKA_USER_CREATE_TOPIC, crud))
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
