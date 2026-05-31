from __future__ import annotations

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, status

from ...api.dependencies import get_db
from ...validation.schemas import PublishRequest, TestInput, TestSummary, TestView
from ..auth.dependencies import get_current_user, require_roles
from .service import create_test, delete_test_for_user, get_test_for_user, list_tests, set_test_publication_for_user, update_test_for_user

router = APIRouter(prefix="/api/tests", tags=["tests"])


@router.get("", response_model=list[TestSummary], responses={401: {"description": "Unauthorized"}})
def read_tests(
    current_user: Annotated[dict, Depends(get_current_user)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return list_tests(connection, current_user)


@router.get(
    "/{test_id}",
    response_model=TestView,
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "Test not found"}, 422: {"description": "Validation error"}},
)
def read_test(
    test_id: int,
    current_user: Annotated[dict, Depends(get_current_user)],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return get_test_for_user(connection, test_id, current_user)


@router.post(
    "",
    response_model=TestView,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"description": "Malformed request body"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        422: {"description": "Validation error"},
    },
)
def create_new_test(
    payload: TestInput,
    current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return create_test(connection, payload.model_dump(), owner_id=current_user["id"])


@router.put(
    "/{test_id}",
    response_model=TestView,
    responses={
        400: {"description": "Malformed request body"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Test not found"},
        422: {"description": "Validation error"},
    },
)
def update_existing_test(
    test_id: int,
    payload: TestInput,
    current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return update_test_for_user(connection, test_id, payload.model_dump(), current_user)


@router.delete(
    "/{test_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "Test not found"}},
)
def remove_test(
    test_id: int,
    current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    delete_test_for_user(connection, test_id, current_user)
    return None


@router.post(
    "/{test_id}/publish",
    response_model=TestSummary,
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}, 404: {"description": "Test not found"}, 422: {"description": "Validation error"}},
)
def publish_test(
    test_id: int,
    payload: PublishRequest,
    current_user: Annotated[dict, Depends(require_roles("teacher", "admin"))],
    connection: Annotated[sqlite3.Connection, Depends(get_db)],
):
    return set_test_publication_for_user(connection, test_id, payload.is_published, current_user)
