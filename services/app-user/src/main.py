import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as prom_metrics
from src.api import main_router, user_router
from src.cache import CacheClient
from src.core.config import settings
from src.core.const import CUSTOM_BUCKETS
from src.core.logger import log
from src.core.tracing import setup_tracing
from src.crud import UserCRUD, get_user_crud
from src.db import AsyncSessionLocal
from src.kafka import KafkaClient
from src.services.main_process import start_main_process

# ── Suppress access logs for health/metrics endpoints ──────────
_NOISELESS_PATHS = {"/liveness", "/readiness", "/metrics"}


class _HealthFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(path in msg for path in _NOISELESS_PATHS)


logging.getLogger("uvicorn.access").addFilter(_HealthFilter())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    cache = CacheClient(settings.redis_host, settings.redis_port, settings.cache_ttl_seconds)
    crud = UserCRUD(AsyncSessionLocal, cache)
    app.dependency_overrides[get_user_crud] = crud
    kafka_client = KafkaClient(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        topic_to_consume=settings.kafka_user_create_topic,
        producer_enabled=False,
    )

    await start_main_process(kafka_client, crud)
    log.info("API Started")
    yield
    await cache.close()
    log.warning("API Stopped")
    return


app = FastAPI(title="User API", lifespan=lifespan)
setup_tracing(service_name="user", app=app)


@app.get(path="/", include_in_schema=False)
def index(req: Request) -> RedirectResponse:
    return RedirectResponse(str(req.base_url) + "docs")


app.include_router(main_router)
app.include_router(user_router)

instrumentator = Instrumentator(
    should_group_status_codes=False,  # Не группировать 2xx, 3xx
    should_instrument_requests_inprogress=True,  # Считать запросы в обработке
)

instrumentator.add(prom_metrics.requests())
instrumentator.add(prom_metrics.latency(buckets=CUSTOM_BUCKETS))
instrumentator.add(prom_metrics.request_size())
instrumentator.add(prom_metrics.response_size())

instrumentator.instrument(app).expose(app)
