from __future__ import annotations

import sqlite3

from fastapi import HTTPException, status

from ...db import repositories
from ..common import get_test_summary_row, parse_datetime, utc_now_iso


def row_to_test_summary(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "is_published": bool(row["is_published"]),
        "owner_id": row["owner_id"],
        "owner_name": row["owner_name"],
        "question_count": repositories.count_questions_for_test(connection, row["id"]),
        "attempt_count": repositories.count_attempts_for_test(connection, row["id"]),
        "updated_at": parse_datetime(row["updated_at"]),
    }


def list_tests(connection: sqlite3.Connection, user: dict) -> list[dict]:
    if user["role"] == "student":
        rows = repositories.fetch_published_test_rows(connection)
    elif user["role"] == "teacher":
        rows = repositories.fetch_test_rows_by_owner(connection, user["id"])
    else:
        rows = repositories.fetch_all_test_rows(connection)
    return [row_to_test_summary(connection, row) for row in rows]


def ensure_test_manage_access(test_row: sqlite3.Row, user: dict) -> None:
    if user["role"] == "admin":
        return
    if user["role"] == "teacher" and test_row["owner_id"] == user["id"]:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this test.")


def ensure_test_read_access(test_row: sqlite3.Row, user: dict) -> None:
    if user["role"] == "admin":
        return
    if user["role"] == "teacher" and test_row["owner_id"] == user["id"]:
        return
    if user["role"] == "student" and bool(test_row["is_published"]):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions for this test.")


def _insert_questions(connection: sqlite3.Connection, test_id: int, questions: list[dict]) -> None:
    with connection:
        for question_position, question in enumerate(questions, start=1):
            question_id = repositories.insert_question(
                connection,
                test_id=test_id,
                prompt=question["prompt"],
                explanation=question.get("explanation", ""),
                position=question_position,
            )
            for option_position, option in enumerate(question["options"], start=1):
                repositories.insert_option(
                    connection,
                    question_id=question_id,
                    text=option["text"],
                    is_correct=option["is_correct"],
                    position=option_position,
                )


def create_test(connection: sqlite3.Connection, payload: dict, owner_id: int) -> dict:
    timestamp = utc_now_iso()
    test_id = repositories.insert_test(
        connection,
        owner_id=owner_id,
        title=payload["title"],
        description=payload.get("description", ""),
        is_published=payload.get("is_published", False),
        created_at=timestamp,
        updated_at=timestamp,
    )
    _insert_questions(connection, test_id, payload["questions"])
    return get_test_detail(connection, test_id, include_correct=True)


def update_test(connection: sqlite3.Connection, test_id: int, payload: dict) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")

    repositories.update_test_record(
        connection,
        test_id=test_id,
        title=payload["title"],
        description=payload.get("description", ""),
        is_published=payload.get("is_published", False),
        updated_at=utc_now_iso(),
    )
    repositories.delete_questions_for_test(connection, test_id)
    _insert_questions(connection, test_id, payload["questions"])
    return get_test_detail(connection, test_id, include_correct=True)


def update_test_for_user(connection: sqlite3.Connection, test_id: int, payload: dict, user: dict) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    ensure_test_manage_access(test_row, user)
    return update_test(connection, test_id, payload)


def delete_test(connection: sqlite3.Connection, test_id: int) -> None:
    deleted = repositories.delete_test_record(connection, test_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")


def delete_test_for_user(connection: sqlite3.Connection, test_id: int, user: dict) -> None:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    ensure_test_manage_access(test_row, user)
    delete_test(connection, test_id)


def set_test_publication(connection: sqlite3.Connection, test_id: int, is_published: bool) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    repositories.update_test_publication_record(
        connection,
        test_id=test_id,
        is_published=is_published,
        updated_at=utc_now_iso(),
    )
    refreshed = repositories.fetch_test_summary_row(connection, test_id)
    return row_to_test_summary(connection, refreshed)


def set_test_publication_for_user(connection: sqlite3.Connection, test_id: int, is_published: bool, user: dict) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    ensure_test_manage_access(test_row, user)
    return set_test_publication(connection, test_id, is_published)


def get_test_detail(connection: sqlite3.Connection, test_id: int, *, include_correct: bool) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")

    questions: list[dict] = []
    for question_row in repositories.fetch_question_rows_for_test(connection, test_id):
        option_rows = repositories.fetch_option_rows_for_question(connection, question_row["id"])
        questions.append(
            {
                "id": question_row["id"],
                "prompt": question_row["prompt"],
                "explanation": question_row["explanation"],
                "position": question_row["position"],
                "options": [
                    {
                        "id": option_row["id"],
                        "text": option_row["text"],
                        "position": option_row["position"],
                        "is_correct": bool(option_row["is_correct"]) if include_correct else None,
                    }
                    for option_row in option_rows
                ],
            }
        )

    return {
        "id": test_row["id"],
        "title": test_row["title"],
        "description": test_row["description"],
        "is_published": bool(test_row["is_published"]),
        "owner_id": test_row["owner_id"],
        "owner_name": test_row["owner_name"],
        "created_at": parse_datetime(test_row["created_at"]),
        "updated_at": parse_datetime(test_row["updated_at"]),
        "questions": questions,
    }


def get_test_for_user(connection: sqlite3.Connection, test_id: int, user: dict) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    ensure_test_read_access(test_row, user)
    include_correct = user["role"] != "student"
    return get_test_detail(connection, test_id, include_correct=include_correct)


__all__ = [
    "create_test",
    "delete_test",
    "delete_test_for_user",
    "ensure_test_manage_access",
    "ensure_test_read_access",
    "get_test_detail",
    "get_test_for_user",
    "list_tests",
    "row_to_test_summary",
    "set_test_publication",
    "set_test_publication_for_user",
    "update_test",
    "update_test_for_user",
]
