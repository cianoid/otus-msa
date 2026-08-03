"""Kafka producer — sends messages asynchronously to configured topics."""

from __future__ import annotations

import json

from aiokafka import AIOKafkaProducer
from src.core.config import settings
from src.core.logger import log

_producer: AIOKafkaProducer | None = None


async def start_producer() -> AIOKafkaProducer:
    """Start and return a cached singleton AIOKafkaProducer (idempotent)."""
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await _producer.start()
        log.info("Kafka producer started (bootstrap: %s)", settings.kafka_bootstrap_servers)
    return _producer


async def _get_producer() -> AIOKafkaProducer:
    """Return the cached AIOKafkaProducer, starting it if needed."""
    return await start_producer()


async def send_user_created(username: str, email: str) -> None:
    """Send a user.create event to Kafka.

    Key:   user_id (string)
    Body:  {"username": str, "email": str}
    """
    producer = await _get_producer()
    value = {"username": username, "email": email}
    await producer.send_and_wait(topic=settings.kafka_user_create_topic, key=username, value=value)
    log.info("Sent user.create: username=%s topic=%s", username, settings.kafka_user_create_topic)


async def stop_producer() -> None:
    """Gracefully stop the Kafka producer (called on app shutdown)."""
    global _producer
    if _producer is not None:
        await _producer.stop()
        _producer = None
        log.info("Kafka producer stopped")
