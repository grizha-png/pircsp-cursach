from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings, get_settings
from .database import get_connection, init_db
from .schemas import (
    AttemptSubmitRequest,
    AttemptView,
    AuthResponse,
    LoginRequest,
    PublishRequest,
    RegistrationRequest,
    TestInput,
    TestSummary,
    TestView,
    UserCreate,
    UserPublic,
    UserUpdate,
)
from .seed import seed_demo_data
from . import services

bearer_scheme = HTTPBearer(auto_error=False)


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

    @app.get("/api/health")
    def healthcheck() -> dict:
        return {"status": "ok"}

    @app.post("/api/auth/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
    def register(payload: RegistrationRequest, connection: Annotated[sqlite3.Connection, Depends(get_db)], request: Request):
        return services.register_student(
            connection,
            username=payload.username,
            full_name=payload.full_name,
            password=payload.password,
            ttl_hours=request.app.state.settings.token_ttl_hours,
        )

    @app.post("/api/auth/login", response_model=AuthResponse)
    def login(payload: LoginRequest, connection: Annotated[sqlite3.Connection, Depends(get_db)], request: Request):
        return services.authenticate_user(
            connection,
            username=payload.username,
            password=payload.password,
            ttl_hours=request.app.state.settings.token_ttl_hours,
        )

    @app.get("/api/auth/me", response_model=UserPublic)
    def read_me(current_user: Annotated[dict, Depends(get_current_user)]):
        return current_user

    @app.post("/api/auth/logout")
    def logout(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
        _: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        services.delete_session(connection, credentials.credentials)
        return {"message": "Logged out."}

    @app.get("/api/users", response_model=list[UserPublic])
    def read_users(
        _: Annotated[dict, Depends(require_roles("admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.list_users(connection)

    @app.post("/api/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
    def create_new_user(
        payload: UserCreate,
        _: Annotated[dict, Depends(require_roles("admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.create_user(connection, **payload.model_dump())

    @app.put("/api/users/{user_id}", response_model=UserPublic)
    def update_existing_user(
        user_id: int,
        payload: UserUpdate,
        current_user: Annotated[dict, Depends(require_roles("admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.update_user(connection, user_id, payload.model_dump(exclude_none=True), current_user["id"])

    @app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_user(
        user_id: int,
        current_user: Annotated[dict, Depends(require_roles("admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        services.delete_user(connection, user_id, current_user["id"])
        return None

    @app.get("/api/tests", response_model=list[TestSummary])
    def read_tests(
        current_user: Annotated[dict, Depends(get_current_user)],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.list_tests(connection, current_user)

    @app.get("/api/tests/{test_id}", response_model=TestView)
    def read_test(
        test_id: int,
        current_user: Annotated[dict, Depends(get_current_user)],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        test_row = services.get_test_summary_row(connection, test_id)
        if not test_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
        services.ensure_test_read_access(test_row, current_user)
        include_correct = current_user["role"] != "student"
        return services.get_test_detail(connection, test_id, include_correct=include_correct)

    @app.post("/api/tests", response_model=TestView, status_code=status.HTTP_201_CREATED)
    def create_new_test(
        payload: TestInput,
        current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.create_test(connection, payload.model_dump(), owner_id=current_user["id"])

    @app.put("/api/tests/{test_id}", response_model=TestView)
    def update_existing_test(
        test_id: int,
        payload: TestInput,
        current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        test_row = services.get_test_summary_row(connection, test_id)
        if not test_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
        services.ensure_test_manage_access(test_row, current_user)
        return services.update_test(connection, test_id, payload.model_dump())

    @app.delete("/api/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
    def remove_test(
        test_id: int,
        current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        test_row = services.get_test_summary_row(connection, test_id)
        if not test_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
        services.ensure_test_manage_access(test_row, current_user)
        services.delete_test(connection, test_id)
        return None

    @app.post("/api/tests/{test_id}/publish", response_model=TestSummary)
    def publish_test(
        test_id: int,
        payload: PublishRequest,
        current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        test_row = services.get_test_summary_row(connection, test_id)
        if not test_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
        services.ensure_test_manage_access(test_row, current_user)
        return services.set_test_publication(connection, test_id, payload.is_published)

    @app.post("/api/tests/{test_id}/submit", response_model=AttemptView)
    def submit_test(
        test_id: int,
        payload: AttemptSubmitRequest,
        current_user: Annotated[dict, Depends(require_roles("student"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.submit_attempt(connection, test_id, current_user["id"], [answer.model_dump() for answer in payload.answers])

    @app.get("/api/attempts/me", response_model=list[AttemptView])
    def read_my_attempts(
        current_user: Annotated[dict, Depends(require_roles("student"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        return services.list_attempts_for_student(connection, current_user["id"])

    @app.get("/api/tests/{test_id}/attempts", response_model=list[AttemptView])
    def read_test_attempts(
        test_id: int,
        current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
        connection: Annotated[sqlite3.Connection, Depends(get_db)],
    ):
        test_row = services.get_test_summary_row(connection, test_id)
        if not test_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
        services.ensure_test_manage_access(test_row, current_user)
        return services.list_attempts_for_test(connection, test_id)

    return app


def get_db(request: Request):
    connection = get_connection(request.app.state.settings.database_path)
    try:
        yield connection
    finally:
        connection.close()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token.")
    user = services.get_user_by_token(connection, credentials.credentials)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")
    return user


def require_roles(*roles: str):
    def role_checker(current_user: Annotated[dict, Depends(get_current_user)]) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions.")
        return current_user

    return role_checker


app = create_app()
