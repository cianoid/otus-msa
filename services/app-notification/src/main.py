import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as prom_metrics
from src.api import main_router, notification_router
from src.core.config import settings
from src.core.const import CUSTOM_BUCKETS
from src.core.logger import log
from src.core.tracing import setup_tracing
from src.crud import get_notification_crud
from src.kafka import KafkaClient
from src.services.email import EmailService
from src.services.main_process import start_main_process

_NOISELESS_PATHS = {"/liveness", "/readiness", "/metrics"}


class _HealthFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(path in msg for path in _NOISELESS_PATHS)


logging.getLogger("uvicorn.access").addFilter(_HealthFilter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    notification_crud = get_notification_crud()
    app.dependency_overrides[get_notification_crud] = notification_crud
    email_service = EmailService(Path(settings.template_dir), notification_crud)
    kafka_client = KafkaClient(
        bootstrap_servers=settings.kafka_bootstrap_servers, topic_to_consume=settings.kafka_send_email_topic
    )

    await start_main_process(kafka_client, email_service)
    log.info("API Started")
    yield
    log.warning("API Stopped")
    return


app = FastAPI(title="Notification API", lifespan=lifespan)
setup_tracing(service_name="notification", app=app)

app.include_router(main_router)
app.include_router(notification_router)

instrumentator = Instrumentator(
    should_group_status_codes=False,  # Не группировать 2xx, 3xx
    should_instrument_requests_inprogress=True,  # Считать запросы в обработке
)

instrumentator.add(prom_metrics.requests())
instrumentator.add(prom_metrics.latency(buckets=CUSTOM_BUCKETS))
instrumentator.add(prom_metrics.request_size())
instrumentator.add(prom_metrics.response_size())

instrumentator.instrument(app).expose(app)
