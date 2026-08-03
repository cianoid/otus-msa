from __future__ import annotations

import asyncio

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from orjson import orjson
from src.core.config import settings
from src.core.logger import log

_consumer_task: asyncio.Task[None] | None = None


class KafkaClient:
    @staticmethod
    def _encode(data):
        if isinstance(data, dict):
            return orjson.dumps(data)
        if not isinstance(data, str):
            data = str(data)
        return data.encode()

    def __call__(self):
        return self

    def __init__(
        self,
        bootstrap_servers: str,
        topic_to_consume: str | None = None,
        consumer_enabled: bool = True,
        producer_enabled: bool = True,
    ):
        if topic_to_consume is None:
            consumer_enabled = False
        self.consumer_enabled = consumer_enabled
        self.producer_enabled = producer_enabled

        if self.consumer_enabled:
            self.consumer = AIOKafkaConsumer(
                topic_to_consume,
                bootstrap_servers=bootstrap_servers,
                group_id=settings.app_title,
                client_id=settings.app_title,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                value_deserializer=lambda v: orjson.loads(v.decode("utf-8")) if v else None,
                max_poll_records=1,
            )
            log.info(
                "Kafka consumer configured (bootstrap: %s, client_id: %s, topic_to_consume: %s)",
                bootstrap_servers,
                settings.app_title,
                topic_to_consume,
            )

        if self.producer_enabled:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                key_serializer=self._encode,
                value_serializer=self._encode,
                request_timeout_ms=2_000,
                client_id=settings.app_title,
            )
            log.info("Kafka producer configured (bootstrap: %s, client_id: %s)", bootstrap_servers, settings.app_title)

    async def send(self, msg: ConsumerRecord, topic: str) -> None:
        if not self.producer_enabled:
            log.warning("Can't send message while producer is disabled")
            return

        try:
            log.info("%s: About to send message to %s with data=%s", msg.key, topic, msg.value)
            await self.producer.send_and_wait(topic=topic, value=msg.value, key=msg.key)
        except Exception as err:
            log.error("Error while sending message to topic_to_consume %s: %s", topic, err)
        else:
            log.info("%s: Sent message to %s with data=%s", msg.key, topic, msg.value)

    async def _start_consumer(self) -> None:
        """Start the Kafka consumer as a background task (idempotent)."""
        if not self.consumer_enabled:
            log.warning("Can't start consume while consumer is disabled")
            return

        global _consumer_task

        if not settings.kafka_bootstrap_servers:
            log.warning("KAFKA_BOOTSTRAP_SERVERS not configured — Kafka consumer disabled")
            return

        if _consumer_task is not None and not _consumer_task.done():
            log.warning("Kafka consumer already running — skipping duplicate start")
            return

        await self.consumer.start()
        log.info("Kafka consumer started")

    async def _stop_consumer(self) -> None:
        """Gracefully stop the Kafka consumer (called on app shutdown)."""
        if not self.consumer_enabled:
            log.warning("Can't stop consume while consumer is disabled")
            return

        global _consumer_task
        if _consumer_task is not None and not _consumer_task.done():
            _consumer_task.cancel()
            try:
                await _consumer_task
            except asyncio.CancelledError:
                pass
            _consumer_task = None
            log.info("Kafka consumer task cancelled and awaited")

    async def start(self) -> None:
        if self.consumer_enabled:
            await self._start_consumer()
        if self.producer_enabled:
            await self.producer.start()

    async def stop(self) -> None:
        if self.consumer_enabled:
            await self._stop_consumer()
        if self.producer_enabled:
            await self.producer.stop()


def get_kafka() -> KafkaClient:
    raise NotImplementedError
