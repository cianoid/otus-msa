from src.core.config import settings
from src.core.logger import log
from src.core.tracing import kafka_inject_headers
from src.kafka import KafkaClient


async def send_user_created(kafka: KafkaClient, username: str, email: str) -> None:
    """Send a user.create event to Kafka.
    Key:   user_id (string)
    Body:  {"username": str, "email": str}
    """
    value = {"username": username, "email": email}
    headers = kafka_inject_headers()
    await kafka.producer.send_and_wait(
        topic=settings.kafka_user_create_topic, key=username, value=value, headers=headers
    )
    log.info("Sent user.create: username=%s topic=%s", username, settings.kafka_user_create_topic)
