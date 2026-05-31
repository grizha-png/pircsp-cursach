from __future__ import annotations

import sqlite3

from fastapi import HTTPException, status

from ...db import repositories
from ..common import parse_datetime, utc_now_iso
from ..tests.service import ensure_test_manage_access


def build_attempt_view(connection: sqlite3.Connection, attempt_row: sqlite3.Row, *, include_student: bool) -> dict:
    return {
        "id": attempt_row["id"],
        "test_id": attempt_row["test_id"],
        "test_title": attempt_row["title"],
        "student_id": attempt_row["user_id"] if include_student else None,
        "student_name": attempt_row["student_name"] if include_student else None,
        "score": attempt_row["score"],
        "total_questions": attempt_row["total_questions"],
        "submitted_at": parse_datetime(attempt_row["submitted_at"]),
        "answers": [
            {
                "question_id": answer_row["question_id"],
                "option_id": answer_row["option_id"],
                "is_correct": bool(answer_row["is_correct"]),
            }
            for answer_row in repositories.fetch_attempt_answer_rows(connection, attempt_row["id"])
        ],
    }


def list_attempts_for_student(connection: sqlite3.Connection, student_id: int) -> list[dict]:
    rows = repositories.fetch_attempt_rows_by_student(connection, student_id)
    return [build_attempt_view(connection, row, include_student=False) for row in rows]


def list_attempts_for_test(connection: sqlite3.Connection, test_id: int) -> list[dict]:
    rows = repositories.fetch_attempt_rows_by_test(connection, test_id)
    return [build_attempt_view(connection, row, include_student=True) for row in rows]


def list_attempts_for_test_for_user(connection: sqlite3.Connection, test_id: int, user: dict) -> list[dict]:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    ensure_test_manage_access(test_row, user)
    return list_attempts_for_test(connection, test_id)


def submit_attempt(connection: sqlite3.Connection, test_id: int, student_id: int, answers: list[dict]) -> dict:
    test_row = repositories.fetch_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    if not bool(test_row["is_published"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test is not published.")

    question_ids = repositories.fetch_question_ids_for_test(connection, test_id)
    if len(answers) != len(question_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Every question must be answered exactly once.",
        )

    submitted_question_ids = [answer["question_id"] for answer in answers]
    if sorted(submitted_question_ids) != sorted(question_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Answers do not match the test questions.")
    if len(set(submitted_question_ids)) != len(submitted_question_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate answers are not allowed.")

    option_map = {
        row["id"]: row["question_id"]
        for row in repositories.fetch_option_rows_for_questions(connection, question_ids)
    }
    correct_options = {
        row["question_id"]: row["id"]
        for row in repositories.fetch_correct_option_rows_for_questions(connection, question_ids)
    }

    score = 0
    evaluated_answers: list[dict] = []
    for answer in answers:
        option_question_id = option_map.get(answer["option_id"])
        if option_question_id != answer["question_id"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Option does not belong to the question.")
        is_correct = correct_options.get(answer["question_id"]) == answer["option_id"]
        if is_correct:
            score += 1
        evaluated_answers.append(
            {
                "question_id": answer["question_id"],
                "option_id": answer["option_id"],
                "is_correct": is_correct,
            }
        )

    submitted_at = utc_now_iso()
    attempt_id = repositories.insert_attempt(
        connection,
        test_id=test_id,
        user_id=student_id,
        score=score,
        total_questions=len(question_ids),
        submitted_at=submitted_at,
    )
    with connection:
        for answer in evaluated_answers:
            repositories.insert_attempt_answer(
                connection,
                attempt_id=attempt_id,
                question_id=answer["question_id"],
                option_id=answer["option_id"],
                is_correct=answer["is_correct"],
            )

    row = repositories.fetch_attempt_row(connection, attempt_id)
    return build_attempt_view(connection, row, include_student=False)


__all__ = [
    "build_attempt_view",
    "list_attempts_for_student",
    "list_attempts_for_test",
    "list_attempts_for_test_for_user",
    "submit_attempt",
]
