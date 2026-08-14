import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as prom_metrics
from src.api import main_router, order_router
from src.core.config import settings
from src.core.const import CUSTOM_BUCKETS
from src.core.logger import log
from src.core.tracing import setup_tracing
from src.crud import OrderCRUD, get_order_crud
from src.db import AsyncSessionLocal
from src.kafka import KafkaClient, get_kafka

# ── Suppress access logs for health/metrics endpoints ──────────
_NOISELESS_PATHS = {"/liveness", "/readiness", "/metrics"}


class _HealthFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(path in msg for path in _NOISELESS_PATHS)


logging.getLogger("uvicorn.access").addFilter(_HealthFilter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    kafka_client = KafkaClient(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        consumer_enabled=False,
    )
    app.dependency_overrides[get_order_crud] = OrderCRUD(AsyncSessionLocal)
    app.dependency_overrides[get_kafka] = kafka_client

    await kafka_client.start()
    log.info("API Started")
    yield
    await kafka_client.stop()
    log.warning("API Stopped")
    return


app = FastAPI(title="Order API", lifespan=lifespan)
setup_tracing(service_name="order", app=app)


@app.get(path="/", include_in_schema=False)
def index(req: Request) -> RedirectResponse:
    return RedirectResponse(str(req.base_url) + "docs")


app.include_router(main_router)
app.include_router(order_router)

instrumentator = Instrumentator(
    should_group_status_codes=False,  # Не группировать 2xx, 3xx
    should_instrument_requests_inprogress=True,  # Считать запросы в обработке
)

instrumentator.add(prom_metrics.requests())
instrumentator.add(prom_metrics.latency(buckets=CUSTOM_BUCKETS))
instrumentator.add(prom_metrics.request_size())
instrumentator.add(prom_metrics.response_size())

instrumentator.instrument(app).expose(app)
