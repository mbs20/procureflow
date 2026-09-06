from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from procureflow.api.v1.router import api_v1_router
from procureflow.config import get_settings
from procureflow.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize DB schemas on startup if needed
    await init_db()
    yield
    # Teardown logic if needed on shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Open-source AI-assisted RFQ comparison and procurement decision engine.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API Routers
    app.include_router(api_v1_router)

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs_url": "/docs",
            "health_url": "/api/v1/health",
        }

    return app


app = create_app()
