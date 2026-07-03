"""FastAPI application factory. Entry point: `uvicorn app.main:app`."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.observability import setup_observability
from app.services.exceptions import DomainError


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Place for startup checks / connection warmups; teardown after `yield`.
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="SmartCourse API", version="0.1.0", lifespan=lifespan)
    setup_observability(app)

    # Allow the browser SPA (different origin) to call the API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(DomainError)
    async def _domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
