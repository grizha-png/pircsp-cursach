from __future__ import annotations

from fastapi import Request

from ..db.database import get_connection


def get_db(request: Request):
    connection = get_connection(request.app.state.settings.database_path)
    try:
        yield connection
    finally:
        connection.close()
