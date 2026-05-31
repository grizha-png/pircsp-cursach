from __future__ import annotations

import random
import string

import pytest
from fastapi.testclient import TestClient


def random_text(length: int) -> str:
    alphabet = string.ascii_letters + string.digits + "_-!@#$%^&*()"
    return "".join(random.choice(alphabet) for _ in range(length))


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "full_name": "Короткий логин", "password": "student123", "role": "student", "is_active": True},
        {"username": "user bad", "full_name": "Пробел в логине", "password": "student123", "role": "student", "is_active": True},
        {"username": "user_ok", "full_name": "Неизвестная роль", "password": "student123", "role": "superuser", "is_active": True},
        {"username": random_text(33), "full_name": "Слишком длинный логин", "password": "student123", "role": "teacher", "is_active": True},
    ],
)
def test_fuzz_user_creation_validation(client: TestClient, auth_headers, payload: dict) -> None:
    headers = auth_headers("admin", "admin123")
    response = client.post("/api/users", headers=headers, json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {
            "title": "bad-1",
            "description": "Нет вопросов",
            "is_published": False,
            "questions": [],
        },
        {
            "title": "bad-2",
            "description": "Один вариант ответа",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Невалидный вопрос?",
                    "explanation": "",
                    "options": [{"text": "Один", "is_correct": True}],
                }
            ],
        },
        {
            "title": "bad-3",
            "description": "Несколько правильных ответов",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Сколько правильных ответов допустимо?",
                    "explanation": "",
                    "options": [
                        {"text": "Один", "is_correct": True},
                        {"text": "Два", "is_correct": True},
                    ],
                }
            ],
        },
        {
            "title": random_text(170),
            "description": "Слишком длинный заголовок",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Проверка длины строки для теста.",
                    "explanation": "",
                    "options": [
                        {"text": "Да", "is_correct": True},
                        {"text": "Нет", "is_correct": False},
                    ],
                }
            ],
        },
    ],
)
def test_fuzz_test_constructor_validation(client: TestClient, auth_headers, payload: dict) -> None:
    headers = auth_headers("teacher", "teacher123")
    response = client.post("/api/tests", headers=headers, json=payload)
    assert response.status_code == 422


def test_fuzz_broken_attempt_payload(client: TestClient, auth_headers) -> None:
    student_headers = auth_headers("student", "student123")
    tests_response = client.get("/api/tests", headers=student_headers)
    test_id = tests_response.json()[0]["id"]
    detail = client.get(f"/api/tests/{test_id}", headers=student_headers).json()
    first_question = detail["questions"][0]

    response = client.post(
        f"/api/tests/{test_id}/submit",
        headers=student_headers,
        json={
            "answers": [
                {"question_id": first_question["id"], "option_id": 999999},
            ]
        },
    )
    assert response.status_code == 400


def test_huge_test_id_is_rejected_before_database_lookup(client: TestClient, auth_headers) -> None:
    student_headers = auth_headers("student", "student123")
    response = client.get("/api/tests/6113989177382905315328", headers=student_headers)
    assert response.status_code == 422


def test_fuzz_role_escalation_attempt_is_blocked(client: TestClient, auth_headers) -> None:
    student_headers = auth_headers("student", "student123")
    response = client.get("/api/users", headers=student_headers)
    assert response.status_code == 403


def test_public_registration_cannot_set_privileged_role(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "username": "evilteacher",
            "full_name": "Попытка Эскалации",
            "password": "student123",
            "role": "teacher",
        },
    )
    assert response.status_code == 422
