from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials

from ...api.dependencies import get_db
from ...validation.schemas import AuthResponse, LoginRequest, RegistrationRequest, UserPublic
from .dependencies import bearer_scheme, get_current_user
from .service import authenticate_user, delete_session, register_student

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"description": "Validation error"}, 409: {"description": "Username already exists"}},
)
def register(
    payload: RegistrationRequest,
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
    request: Request,
):
    return register_student(
        connection,
        username=payload.username,
        full_name=payload.full_name,
        password=payload.password,
        ttl_hours=request.app.state.settings.token_ttl_hours,
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={401: {"description": "Invalid credentials"}, 403: {"description": "Inactive user"}, 422: {"description": "Validation error"}},
)
def login(
    payload: LoginRequest,
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
    request: Request,
):
    return authenticate_user(
        connection,
        username=payload.username,
        password=payload.password,
        ttl_hours=request.app.state.settings.token_ttl_hours,
    )


@router.get("/me", response_model=UserPublic, responses={401: {"description": "Unauthorized"}})
def read_me(current_user: Annotated[dict, Depends(get_current_user)]):
    return current_user


@router.post("/logout", responses={401: {"description": "Unauthorized"}})
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
    _: Annotated[dict, Depends(get_current_user)],
) -> dict:
    delete_session(connection, credentials.credentials)
    return {"message": "Logged out."}
