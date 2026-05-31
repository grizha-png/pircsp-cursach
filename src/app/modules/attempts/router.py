from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Path

from ...api.dependencies import get_db
from ...validation.schemas import AttemptSubmitRequest, AttemptView
from ..auth.dependencies import require_roles
from .service import list_attempts_for_student, list_attempts_for_test_for_user, submit_attempt

router = APIRouter(tags=["attempts"])
TestId = Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]


@router.post(
    "/api/tests/{test_id}/submit",
    response_model=AttemptView,
    responses={400: {"description": "Bad request"}, 401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "Test not found"}, 422: {"description": "Validation error"}},
)
def submit_test(
    test_id: TestId,
    payload: AttemptSubmitRequest,
    current_user: Annotated[dict, Depends(require_roles("student"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return submit_attempt(connection, test_id, current_user["id"], [answer.model_dump() for answer in payload.answers])


@router.get("/api/attempts/me", response_model=list[AttemptView], responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}})
def read_my_attempts(
    current_user: Annotated[dict, Depends(require_roles("student"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return list_attempts_for_student(connection, current_user["id"])


@router.get(
    "/api/tests/{test_id}/attempts",
    response_model=list[AttemptView],
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "Test not found"}, 422: {"description": "Validation error"}},
)
def read_test_attempts(
    test_id: TestId,
    current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return list_attempts_for_test_for_user(connection, test_id, current_user)
