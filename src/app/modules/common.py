from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from ..db import repositories

VALID_ROLES = {"admin", "teacher", "student"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def row_to_user_public(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
        "is_active": bool(row["is_active"]),
    }


def get_user_by_username(connection: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return repositories.fetch_user_by_username(connection, username)


def get_test_summary_row(connection: sqlite3.Connection, test_id: int) -> sqlite3.Row | None:
    return repositories.fetch_test_summary_row(connection, test_id)
