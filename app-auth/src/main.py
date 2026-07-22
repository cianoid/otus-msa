from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from src.api import router as auth_router
from src.db import engine
from src.logger import log


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    log.info("Auth API Started")
    yield
    await engine.dispose()
    log.warning("Auth API Stopped")


app = FastAPI(
    title="Auth API",
    description="JWT-based authentication service",
    lifespan=lifespan,
)


@app.get(path="/", include_in_schema=False)
def index(req: Request) -> RedirectResponse:
    return RedirectResponse(str(req.base_url) + "docs")


app.include_router(auth_router)
