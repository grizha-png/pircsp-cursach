from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from ...api.dependencies import get_db
from ...validation.schemas import AttemptSubmitRequest, AttemptView
from ..auth.dependencies import require_roles
from .service import list_attempts_for_student, list_attempts_for_test_for_user, submit_attempt

router = APIRouter(tags=["attempts"])


@router.post("/api/tests/{test_id}/submit", response_model=AttemptView)
def submit_test(
    test_id: int,
    payload: AttemptSubmitRequest,
    current_user: Annotated[dict, Depends(require_roles("student"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return submit_attempt(connection, test_id, current_user["id"], [answer.model_dump() for answer in payload.answers])


@router.get("/api/attempts/me", response_model=list[AttemptView])
def read_my_attempts(
    current_user: Annotated[dict, Depends(require_roles("student"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return list_attempts_for_student(connection, current_user["id"])


@router.get("/api/tests/{test_id}/attempts", response_model=list[AttemptView])
def read_test_attempts(
    test_id: int,
    current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return list_attempts_for_test_for_user(connection, test_id, current_user)
