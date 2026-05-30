from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status

from .security import generate_token, hash_password, verify_password

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
    return connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users(connection: sqlite3.Connection) -> list[dict]:
    rows = connection.execute(
        "SELECT id, username, full_name, role, is_active FROM users ORDER BY id"
    ).fetchall()
    return [row_to_user_public(row) for row in rows]


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
    if get_user_by_username(connection, username):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")
    created_at = utc_now_iso()
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, full_name, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, full_name, hash_password(password), role, int(is_active), created_at),
        )
    user = get_user_by_id(connection, cursor.lastrowid)
    return row_to_user_public(user)


def update_user(connection: sqlite3.Connection, user_id: int, payload: dict, current_user_id: int) -> dict:
    user = get_user_by_id(connection, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user_id == current_user_id and payload.get("is_active") is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    updated_values = {
        "full_name": payload.get("full_name", user["full_name"]),
        "password_hash": hash_password(payload["password"]) if payload.get("password") else user["password_hash"],
        "role": payload.get("role", user["role"]),
        "is_active": int(payload.get("is_active", bool(user["is_active"]))),
    }
    if updated_values["role"] not in VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role.")

    with connection:
        connection.execute(
            """
            UPDATE users
            SET full_name = ?, password_hash = ?, role = ?, is_active = ?
            WHERE id = ?
            """,
            (
                updated_values["full_name"],
                updated_values["password_hash"],
                updated_values["role"],
                updated_values["is_active"],
                user_id,
            ),
        )
    refreshed = get_user_by_id(connection, user_id)
    return row_to_user_public(refreshed)


def delete_user(connection: sqlite3.Connection, user_id: int, current_user_id: int) -> None:
    user = get_user_by_id(connection, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user_id == current_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account.")
    with connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))


def create_session(connection: sqlite3.Connection, user_id: int, ttl_hours: int) -> str:
    token = generate_token()
    created_at = utc_now()
    expires_at = created_at + timedelta(hours=ttl_hours)
    with connection:
        connection.execute(
            """
            INSERT INTO sessions (user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, token, expires_at.isoformat(), created_at.isoformat()),
        )
    return token


def authenticate_user(connection: sqlite3.Connection, username: str, password: str, ttl_hours: int) -> dict:
    user = get_user_by_username(connection, username)
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
    session = connection.execute(
        """
        SELECT s.id AS session_id, s.expires_at, u.id, u.username, u.full_name, u.role, u.is_active
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()
    if not session:
        return None
    if parse_datetime(session["expires_at"]) <= utc_now():
        with connection:
            connection.execute("DELETE FROM sessions WHERE id = ?", (session["session_id"],))
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
    with connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


def get_test_summary_row(connection: sqlite3.Connection, test_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            t.id,
            t.title,
            t.description,
            t.is_published,
            t.owner_id,
            u.full_name AS owner_name,
            t.created_at,
            t.updated_at
        FROM tests t
        JOIN users u ON u.id = t.owner_id
        WHERE t.id = ?
        """,
        (test_id,),
    ).fetchone()


def row_to_test_summary(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    question_count = connection.execute(
        "SELECT COUNT(*) AS count FROM questions WHERE test_id = ?", (row["id"],)
    ).fetchone()["count"]
    attempt_count = connection.execute(
        "SELECT COUNT(*) AS count FROM attempts WHERE test_id = ?", (row["id"],)
    ).fetchone()["count"]
    return {
        "id": row["id"],
        "title": row["title"],
        "description": row["description"],
        "is_published": bool(row["is_published"]),
        "owner_id": row["owner_id"],
        "owner_name": row["owner_name"],
        "question_count": question_count,
        "attempt_count": attempt_count,
        "updated_at": parse_datetime(row["updated_at"]),
    }


def list_tests(connection: sqlite3.Connection, user: dict) -> list[dict]:
    if user["role"] == "student":
        query = """
            SELECT t.id, t.title, t.description, t.is_published, t.owner_id, u.full_name AS owner_name, t.updated_at
            FROM tests t
            JOIN users u ON u.id = t.owner_id
            WHERE t.is_published = 1
            ORDER BY t.updated_at DESC
        """
        rows = connection.execute(query).fetchall()
    elif user["role"] == "teacher":
        query = """
            SELECT t.id, t.title, t.description, t.is_published, t.owner_id, u.full_name AS owner_name, t.updated_at
            FROM tests t
            JOIN users u ON u.id = t.owner_id
            WHERE t.owner_id = ?
            ORDER BY t.updated_at DESC
        """
        rows = connection.execute(query, (user["id"],)).fetchall()
    else:
        query = """
            SELECT t.id, t.title, t.description, t.is_published, t.owner_id, u.full_name AS owner_name, t.updated_at
            FROM tests t
            JOIN users u ON u.id = t.owner_id
            ORDER BY t.updated_at DESC
        """
        rows = connection.execute(query).fetchall()
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
    for question_position, question in enumerate(questions, start=1):
        question_cursor = connection.execute(
            """
            INSERT INTO questions (test_id, prompt, explanation, position)
            VALUES (?, ?, ?, ?)
            """,
            (test_id, question["prompt"], question.get("explanation", ""), question_position),
        )
        question_id = question_cursor.lastrowid
        for option_position, option in enumerate(question["options"], start=1):
            connection.execute(
                """
                INSERT INTO options (question_id, text, is_correct, position)
                VALUES (?, ?, ?, ?)
                """,
                (question_id, option["text"], int(option["is_correct"]), option_position),
            )


def create_test(connection: sqlite3.Connection, payload: dict, owner_id: int) -> dict:
    timestamp = utc_now_iso()
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO tests (owner_id, title, description, is_published, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                payload["title"],
                payload.get("description", ""),
                int(payload.get("is_published", False)),
                timestamp,
                timestamp,
            ),
        )
        _insert_questions(connection, cursor.lastrowid, payload["questions"])
    return get_test_detail(connection, cursor.lastrowid, include_correct=True)


def update_test(connection: sqlite3.Connection, test_id: int, payload: dict) -> dict:
    test_row = get_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    with connection:
        connection.execute(
            """
            UPDATE tests
            SET title = ?, description = ?, is_published = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload["title"],
                payload.get("description", ""),
                int(payload.get("is_published", False)),
                utc_now_iso(),
                test_id,
            ),
        )
        connection.execute("DELETE FROM questions WHERE test_id = ?", (test_id,))
        _insert_questions(connection, test_id, payload["questions"])
    return get_test_detail(connection, test_id, include_correct=True)


def delete_test(connection: sqlite3.Connection, test_id: int) -> None:
    with connection:
        deleted = connection.execute("DELETE FROM tests WHERE id = ?", (test_id,)).rowcount
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")


def set_test_publication(connection: sqlite3.Connection, test_id: int, is_published: bool) -> dict:
    test_row = get_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    with connection:
        connection.execute(
            "UPDATE tests SET is_published = ?, updated_at = ? WHERE id = ?",
            (int(is_published), utc_now_iso(), test_id),
        )
    refreshed = get_test_summary_row(connection, test_id)
    return row_to_test_summary(connection, refreshed)


def get_test_detail(connection: sqlite3.Connection, test_id: int, *, include_correct: bool) -> dict:
    test_row = get_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    question_rows = connection.execute(
        """
        SELECT id, prompt, explanation, position
        FROM questions
        WHERE test_id = ?
        ORDER BY position
        """,
        (test_id,),
    ).fetchall()
    questions: list[dict] = []
    for question_row in question_rows:
        option_rows = connection.execute(
            """
            SELECT id, text, is_correct, position
            FROM options
            WHERE question_id = ?
            ORDER BY position
            """,
            (question_row["id"],),
        ).fetchall()
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


def list_attempts_for_student(connection: sqlite3.Connection, student_id: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT a.id, a.test_id, a.user_id, a.score, a.total_questions, a.submitted_at, t.title
        FROM attempts a
        JOIN tests t ON t.id = a.test_id
        WHERE a.user_id = ?
        ORDER BY a.submitted_at DESC
        """,
        (student_id,),
    ).fetchall()
    return [build_attempt_view(connection, row, include_student=False) for row in rows]


def list_attempts_for_test(connection: sqlite3.Connection, test_id: int) -> list[dict]:
    rows = connection.execute(
        """
        SELECT a.id, a.test_id, a.user_id, a.score, a.total_questions, a.submitted_at, t.title, u.full_name AS student_name
        FROM attempts a
        JOIN tests t ON t.id = a.test_id
        JOIN users u ON u.id = a.user_id
        WHERE a.test_id = ?
        ORDER BY a.submitted_at DESC
        """,
        (test_id,),
    ).fetchall()
    return [build_attempt_view(connection, row, include_student=True) for row in rows]


def build_attempt_view(connection: sqlite3.Connection, attempt_row: sqlite3.Row, *, include_student: bool) -> dict:
    answer_rows = connection.execute(
        """
        SELECT question_id, option_id, is_correct
        FROM attempt_answers
        WHERE attempt_id = ?
        ORDER BY id
        """,
        (attempt_row["id"],),
    ).fetchall()
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
            for answer_row in answer_rows
        ],
    }


def submit_attempt(connection: sqlite3.Connection, test_id: int, student_id: int, answers: list[dict]) -> dict:
    test_row = get_test_summary_row(connection, test_id)
    if not test_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found.")
    if not bool(test_row["is_published"]):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Test is not published.")

    question_rows = connection.execute(
        "SELECT id FROM questions WHERE test_id = ? ORDER BY position",
        (test_id,),
    ).fetchall()
    question_ids = [row["id"] for row in question_rows]
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
        for row in connection.execute(
            """
            SELECT id, question_id
            FROM options
            WHERE question_id IN ({placeholders})
            """.format(placeholders=",".join("?" for _ in question_ids)),
            tuple(question_ids),
        ).fetchall()
    }
    correct_options = {
        row["question_id"]: row["id"]
        for row in connection.execute(
            """
            SELECT id, question_id
            FROM options
            WHERE question_id IN ({placeholders}) AND is_correct = 1
            """.format(placeholders=",".join("?" for _ in question_ids)),
            tuple(question_ids),
        ).fetchall()
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
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO attempts (test_id, user_id, score, total_questions, submitted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (test_id, student_id, score, len(question_ids), submitted_at),
        )
        attempt_id = cursor.lastrowid
        for answer in evaluated_answers:
            connection.execute(
                """
                INSERT INTO attempt_answers (attempt_id, question_id, option_id, is_correct)
                VALUES (?, ?, ?, ?)
                """,
                (attempt_id, answer["question_id"], answer["option_id"], int(answer["is_correct"])),
            )

    row = connection.execute(
        """
        SELECT a.id, a.test_id, a.user_id, a.score, a.total_questions, a.submitted_at, t.title
        FROM attempts a
        JOIN tests t ON t.id = a.test_id
        WHERE a.id = ?
        """,
        (attempt_id,),
    ).fetchone()
    return build_attempt_view(connection, row, include_student=False)
