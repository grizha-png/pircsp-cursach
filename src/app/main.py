from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import Settings, get_settings
from .db.database import get_connection, init_db
from .modules.attempts.router import router as attempts_router
from .modules.auth.router import router as auth_router
from .modules.tests.router import router as tests_router
from .modules.users.router import router as users_router
from .seed import seed_demo_data


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db(app_settings.database_path)
        with get_connection(app_settings.database_path) as connection:
            seed_demo_data(connection)
        yield

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.state.settings = app_settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["health"])
    def healthcheck() -> dict:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(tests_router)
    app.include_router(attempts_router)

    return app


app = create_app()
