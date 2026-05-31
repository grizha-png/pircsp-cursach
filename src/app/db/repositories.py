from __future__ import annotations

import sqlite3


def fetch_user_by_username(connection: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def fetch_user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def fetch_all_users(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id, username, full_name, role, is_active FROM users ORDER BY id"
    ).fetchall()


def insert_user(
    connection: sqlite3.Connection,
    *,
    username: str,
    full_name: str,
    password_hash: str,
    role: str,
    is_active: bool,
    created_at: str,
) -> int:
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO users (username, full_name, password_hash, role, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, full_name, password_hash, role, int(is_active), created_at),
        )
    return cursor.lastrowid


def update_user_record(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    full_name: str,
    password_hash: str,
    role: str,
    is_active: bool,
) -> None:
    with connection:
        connection.execute(
            """
            UPDATE users
            SET full_name = ?, password_hash = ?, role = ?, is_active = ?
            WHERE id = ?
            """,
            (full_name, password_hash, role, int(is_active), user_id),
        )


def delete_user_record(connection: sqlite3.Connection, user_id: int) -> None:
    with connection:
        connection.execute("DELETE FROM users WHERE id = ?", (user_id,))


def insert_session(
    connection: sqlite3.Connection,
    *,
    user_id: int,
    token: str,
    expires_at: str,
    created_at: str,
) -> None:
    with connection:
        connection.execute(
            """
            INSERT INTO sessions (user_id, token, expires_at, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, token, expires_at, created_at),
        )


def fetch_user_session_by_token(connection: sqlite3.Connection, token: str) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT s.id AS session_id, s.expires_at, u.id, u.username, u.full_name, u.role, u.is_active
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ?
        """,
        (token,),
    ).fetchone()


def delete_session_by_id(connection: sqlite3.Connection, session_id: int) -> None:
    with connection:
        connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def delete_session_by_token(connection: sqlite3.Connection, token: str) -> None:
    with connection:
        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))


def fetch_test_summary_row(connection: sqlite3.Connection, test_id: int) -> sqlite3.Row | None:
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


def fetch_test_id_by_owner_and_title(connection: sqlite3.Connection, owner_id: int, title: str) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT id FROM tests WHERE owner_id = ? AND title = ?",
        (owner_id, title),
    ).fetchone()


def fetch_published_test_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT t.id, t.title, t.description, t.is_published, t.owner_id, u.full_name AS owner_name, t.updated_at
        FROM tests t
        JOIN users u ON u.id = t.owner_id
        WHERE t.is_published = 1
        ORDER BY t.updated_at DESC
        """
    ).fetchall()


def fetch_test_rows_by_owner(connection: sqlite3.Connection, owner_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT t.id, t.title, t.description, t.is_published, t.owner_id, u.full_name AS owner_name, t.updated_at
        FROM tests t
        JOIN users u ON u.id = t.owner_id
        WHERE t.owner_id = ?
        ORDER BY t.updated_at DESC
        """,
        (owner_id,),
    ).fetchall()


def fetch_all_test_rows(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT t.id, t.title, t.description, t.is_published, t.owner_id, u.full_name AS owner_name, t.updated_at
        FROM tests t
        JOIN users u ON u.id = t.owner_id
        ORDER BY t.updated_at DESC
        """
    ).fetchall()


def count_questions_for_test(connection: sqlite3.Connection, test_id: int) -> int:
    return connection.execute(
        "SELECT COUNT(*) AS count FROM questions WHERE test_id = ?",
        (test_id,),
    ).fetchone()["count"]


def count_attempts_for_test(connection: sqlite3.Connection, test_id: int) -> int:
    return connection.execute(
        "SELECT COUNT(*) AS count FROM attempts WHERE test_id = ?",
        (test_id,),
    ).fetchone()["count"]


def insert_test(
    connection: sqlite3.Connection,
    *,
    owner_id: int,
    title: str,
    description: str,
    is_published: bool,
    created_at: str,
    updated_at: str,
) -> int:
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO tests (owner_id, title, description, is_published, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (owner_id, title, description, int(is_published), created_at, updated_at),
        )
    return cursor.lastrowid


def update_test_record(
    connection: sqlite3.Connection,
    *,
    test_id: int,
    title: str,
    description: str,
    is_published: bool,
    updated_at: str,
) -> None:
    with connection:
        connection.execute(
            """
            UPDATE tests
            SET title = ?, description = ?, is_published = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, description, int(is_published), updated_at, test_id),
        )


def delete_questions_for_test(connection: sqlite3.Connection, test_id: int) -> None:
    with connection:
        connection.execute("DELETE FROM questions WHERE test_id = ?", (test_id,))


def delete_test_record(connection: sqlite3.Connection, test_id: int) -> int:
    with connection:
        result = connection.execute("DELETE FROM tests WHERE id = ?", (test_id,))
    return result.rowcount


def update_test_publication_record(
    connection: sqlite3.Connection,
    *,
    test_id: int,
    is_published: bool,
    updated_at: str,
) -> None:
    with connection:
        connection.execute(
            "UPDATE tests SET is_published = ?, updated_at = ? WHERE id = ?",
            (int(is_published), updated_at, test_id),
        )


def insert_question(
    connection: sqlite3.Connection,
    *,
    test_id: int,
    prompt: str,
    explanation: str,
    position: int,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO questions (test_id, prompt, explanation, position)
        VALUES (?, ?, ?, ?)
        """,
        (test_id, prompt, explanation, position),
    )
    return cursor.lastrowid


def insert_option(
    connection: sqlite3.Connection,
    *,
    question_id: int,
    text: str,
    is_correct: bool,
    position: int,
) -> None:
    connection.execute(
        """
        INSERT INTO options (question_id, text, is_correct, position)
        VALUES (?, ?, ?, ?)
        """,
        (question_id, text, int(is_correct), position),
    )


def fetch_question_rows_for_test(connection: sqlite3.Connection, test_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, prompt, explanation, position
        FROM questions
        WHERE test_id = ?
        ORDER BY position
        """,
        (test_id,),
    ).fetchall()


def fetch_option_rows_for_question(connection: sqlite3.Connection, question_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT id, text, is_correct, position
        FROM options
        WHERE question_id = ?
        ORDER BY position
        """,
        (question_id,),
    ).fetchall()


def fetch_attempt_rows_by_student(connection: sqlite3.Connection, student_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT a.id, a.test_id, a.user_id, a.score, a.total_questions, a.submitted_at, t.title
        FROM attempts a
        JOIN tests t ON t.id = a.test_id
        WHERE a.user_id = ?
        ORDER BY a.submitted_at DESC
        """,
        (student_id,),
    ).fetchall()


def fetch_attempt_rows_by_test(connection: sqlite3.Connection, test_id: int) -> list[sqlite3.Row]:
    return connection.execute(
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


def fetch_attempt_answer_rows(connection: sqlite3.Connection, attempt_id: int) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT question_id, option_id, is_correct
        FROM attempt_answers
        WHERE attempt_id = ?
        ORDER BY id
        """,
        (attempt_id,),
    ).fetchall()


def fetch_question_ids_for_test(connection: sqlite3.Connection, test_id: int) -> list[int]:
    rows = connection.execute(
        "SELECT id FROM questions WHERE test_id = ? ORDER BY position",
        (test_id,),
    ).fetchall()
    return [row["id"] for row in rows]


def fetch_option_rows_for_questions(connection: sqlite3.Connection, question_ids: list[int]) -> list[sqlite3.Row]:
    if not question_ids:
        return []
    placeholders = ",".join("?" for _ in question_ids)
    return connection.execute(
        f"""
        SELECT id, question_id
        FROM options
        WHERE question_id IN ({placeholders})
        """,
        tuple(question_ids),
    ).fetchall()


def fetch_correct_option_rows_for_questions(connection: sqlite3.Connection, question_ids: list[int]) -> list[sqlite3.Row]:
    if not question_ids:
        return []
    placeholders = ",".join("?" for _ in question_ids)
    return connection.execute(
        f"""
        SELECT id, question_id
        FROM options
        WHERE question_id IN ({placeholders}) AND is_correct = 1
        """,
        tuple(question_ids),
    ).fetchall()


def insert_attempt(
    connection: sqlite3.Connection,
    *,
    test_id: int,
    user_id: int,
    score: int,
    total_questions: int,
    submitted_at: str,
) -> int:
    with connection:
        cursor = connection.execute(
            """
            INSERT INTO attempts (test_id, user_id, score, total_questions, submitted_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (test_id, user_id, score, total_questions, submitted_at),
        )
    return cursor.lastrowid


def insert_attempt_answer(
    connection: sqlite3.Connection,
    *,
    attempt_id: int,
    question_id: int,
    option_id: int,
    is_correct: bool,
) -> None:
    connection.execute(
        """
        INSERT INTO attempt_answers (attempt_id, question_id, option_id, is_correct)
        VALUES (?, ?, ?, ?)
        """,
        (attempt_id, question_id, option_id, int(is_correct)),
    )


def fetch_attempt_row(connection: sqlite3.Connection, attempt_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT a.id, a.test_id, a.user_id, a.score, a.total_questions, a.submitted_at, t.title
        FROM attempts a
        JOIN tests t ON t.id = a.test_id
        WHERE a.id = ?
        """,
        (attempt_id,),
    ).fetchone()


def attempt_exists_for_student_and_test(connection: sqlite3.Connection, test_id: int, student_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM attempts WHERE test_id = ? AND user_id = ? LIMIT 1",
        (test_id, student_id),
    ).fetchone()
    return row is not None
