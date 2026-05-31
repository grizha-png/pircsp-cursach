from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, status

from ...api.dependencies import get_db
from ...validation.schemas import UserCreate, UserPublic, UserUpdate
from ..auth.dependencies import require_roles
from .service import create_user, delete_user, list_users, update_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserPublic], responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}})
def read_users(
    _: Annotated[dict, Depends(require_roles("admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return list_users(connection)


@router.post(
    "",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 409: {"description": "Username already exists"}, 422: {"description": "Validation error"}},
)
def create_new_user(
    payload: UserCreate,
    _: Annotated[dict, Depends(require_roles("admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return create_user(connection, **payload.model_dump())


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    responses={400: {"description": "Bad request"}, 401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "User not found"}, 422: {"description": "Validation error"}},
)
def update_existing_user(
    user_id: int,
    payload: UserUpdate,
    current_user: Annotated[dict, Depends(require_roles("admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return update_user(connection, user_id, payload.model_dump(exclude_none=True), current_user["id"])


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={400: {"description": "Bad request"}, 401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "User not found"}},
)
def remove_user(
    user_id: int,
    current_user: Annotated[dict, Depends(require_roles("admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    delete_user(connection, user_id, current_user["id"])
    return None
