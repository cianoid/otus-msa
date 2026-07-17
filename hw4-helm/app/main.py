from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator, metrics as prom_metrics

from app.api import router as api_router
from app.crud import UserCRUD, get_user_crud
from app.db import AsyncSessionLocal
from app.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    app.dependency_overrides[get_user_crud] = UserCRUD(AsyncSessionLocal)
    log.info("API Started")
    yield
    log.warning("API Stopped")
    return


app = FastAPI(title="User Management API", description="Simple CRUD API for user management", lifespan=lifespan)

@app.get(path="/", include_in_schema=False)
def index(req: Request) -> RedirectResponse:  # noqa: D103
    return RedirectResponse(str(req.base_url) + "docs")

app.include_router(api_router)


# 5ms - 10s
CUSTOM_BUCKETS = [
    0.001,
    0.002,
    0.003,   # 3 мс
    0.004,
    0.005,   # 5 мс
    0.01,    # 10 мс
    0.025,   # 25 мс
    0.05,    # 50 мс
    0.1,     # 100 мс
    0.25,    # 250 мс
    0.5,     # 500 мс
    1.0,     # 1 сек
    1.5,     # 1.5 сек
    2.0,     # 2 сек
    3.0,     # 3 сек
    5.0,     # 5 сек
    10.0     # 10 сек
]

instrumentator = Instrumentator(
    should_group_status_codes=False,             # Не группировать 2xx, 3xx
    should_instrument_requests_inprogress=True,  # Считать запросы в обработке
)

instrumentator.add(prom_metrics.requests())
instrumentator.add(prom_metrics.latency(buckets=CUSTOM_BUCKETS))
instrumentator.add(prom_metrics.request_size())
instrumentator.add(prom_metrics.response_size())

instrumentator.instrument(app).expose(app)
