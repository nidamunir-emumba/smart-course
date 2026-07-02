"""FastAPI application factory. Entry point: `uvicorn app.main:app`."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import setup_logging
from app.core.observability import setup_observability


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Place for startup checks / connection warmups; teardown after `yield`.
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="SmartCourse API", version="0.1.0", lifespan=lifespan)
    setup_observability(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
