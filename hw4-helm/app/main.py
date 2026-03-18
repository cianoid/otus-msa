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


# Instrument the app with default metrics
Instrumentator().instrument(app).expose(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
