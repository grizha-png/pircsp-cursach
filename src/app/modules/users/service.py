from __future__ import annotations

import sqlite3

from fastapi import HTTPException, status

from ...core.security import hash_password
from ...db import repositories
from ..common import VALID_ROLES, get_user_by_username, row_to_user_public, utc_now_iso


def list_users(connection: sqlite3.Connection) -> list[dict]:
    return [row_to_user_public(row) for row in repositories.fetch_all_users(connection)]


def create_user(
    connection: sqlite3.Connection,
    *,
    username: str,
    full_name: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> dict:
    if role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role.")
    if repositories.fetch_user_by_username(connection, username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    created_user_id = repositories.insert_user(
        connection,
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
        created_at=utc_now_iso(),
    )
    user = repositories.fetch_user_by_id(connection, created_user_id)
    return row_to_user_public(user)


def update_user(connection: sqlite3.Connection, user_id: int, payload: dict, current_user_id: int) -> dict:
    user = repositories.fetch_user_by_id(connection, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user_id == current_user_id and payload.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    next_role = payload.get("role", user["role"])
    if next_role not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role.")

    repositories.update_user_record(
        connection,
        user_id=user_id,
        full_name=payload.get("full_name", user["full_name"]),
        password_hash=hash_password(payload["password"]) if payload.get("password") else user["password_hash"],
        role=next_role,
        is_active=payload.get("is_active", bool(user["is_active"])),
    )

    refreshed = repositories.fetch_user_by_id(connection, user_id)
    return row_to_user_public(refreshed)


def delete_user(connection: sqlite3.Connection, user_id: int, current_user_id: int) -> None:
    user = repositories.fetch_user_by_id(connection, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user_id == current_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")
    repositories.delete_user_record(connection, user_id)


__all__ = [
    "create_user",
    "delete_user",
    "get_user_by_username",
    "list_users",
    "row_to_user_public",
    "update_user",
]
