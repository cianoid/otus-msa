from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as prom_metrics

from src.api import auth_router, main_router
from src.core.const import CUSTOM_BUCKETS
from src.core.logger import log
from src.crud import UserCRUD, get_user_crud
from src.db import AsyncSessionLocal
from src.kafka import start_producer, stop_producer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.dependency_overrides[get_user_crud] = UserCRUD(AsyncSessionLocal)
    await start_producer()
    log.info("API Started")
    yield
    await stop_producer()
    log.warning("API Stopped")
    return


app = FastAPI(title="Auth API", lifespan=lifespan)


@app.get(path="/", include_in_schema=False)
def index(req: Request) -> RedirectResponse:  # noqa: D103
    return RedirectResponse(str(req.base_url) + "docs")


app.include_router(main_router)
app.include_router(auth_router)

instrumentator = Instrumentator(
    should_group_status_codes=False,  # Не группировать 2xx, 3xx
    should_instrument_requests_inprogress=True,  # Считать запросы в обработке
)

instrumentator.add(prom_metrics.requests())
instrumentator.add(prom_metrics.latency(buckets=CUSTOM_BUCKETS))
instrumentator.add(prom_metrics.request_size())
instrumentator.add(prom_metrics.response_size())

instrumentator.instrument(app).expose(app)
