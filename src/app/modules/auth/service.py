from __future__ import annotations

import sqlite3
from datetime import timedelta

from fastapi import HTTPException, status

from ...core.security import generate_token, verify_password
from ...db import repositories
from ..common import parse_datetime, row_to_user_public, utc_now, utc_now_iso
from ..users.service import create_user


def create_session(connection: sqlite3.Connection, user_id: int, ttl_hours: int) -> str:
    token = generate_token()
    created_at = utc_now()
    expires_at = created_at + timedelta(hours=ttl_hours)
    repositories.insert_session(
        connection,
        user_id=user_id,
        token=token,
        expires_at=expires_at.isoformat(),
        created_at=created_at.isoformat(),
    )
    return token


def authenticate_user(connection: sqlite3.Connection, username: str, password: str, ttl_hours: int) -> dict:
    user = repositories.fetch_user_by_username(connection, username)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    if not bool(user["is_active"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive.")
    token = create_session(connection, user["id"], ttl_hours)
    return {"token": token, "user": row_to_user_public(user)}


def register_student(connection: sqlite3.Connection, username: str, full_name: str, password: str, ttl_hours: int) -> dict:
    user = create_user(
        connection,
        username=username,
        full_name=full_name,
        password=password,
        role="student",
        is_active=True,
    )
    token = create_session(connection, user["id"], ttl_hours)
    return {"token": token, "user": user}


def get_user_by_token(connection: sqlite3.Connection, token: str) -> dict | None:
    session = repositories.fetch_user_session_by_token(connection, token)
    if not session:
        return None
    if parse_datetime(session["expires_at"]) <= utc_now():
        repositories.delete_session_by_id(connection, session["session_id"])
        return None
    if not bool(session["is_active"]):
        return None
    return {
        "id": session["id"],
        "username": session["username"],
        "full_name": session["full_name"],
        "role": session["role"],
        "is_active": bool(session["is_active"]),
    }


def delete_session(connection: sqlite3.Connection, token: str) -> None:
    repositories.delete_session_by_token(connection, token)


__all__ = [
    "authenticate_user",
    "create_session",
    "delete_session",
    "get_user_by_token",
    "register_student",
]
