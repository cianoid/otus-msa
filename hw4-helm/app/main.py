from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from prometheus_fastapi_instrumentator import Instrumentator

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


# 5ms - 5s
CUSTOM_BUCKETS = [
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
]

instrumentator = Instrumentator(
    should_group_status_codes=False,             # Не группировать 2xx, 3xx
    should_instrument_requests_inprogress=True,  # Считать запросы в обработке
)

instrumentator.instrument(app).expose(app)
