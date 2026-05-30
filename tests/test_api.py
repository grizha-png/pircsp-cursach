from __future__ import annotations

from fastapi.testclient import TestClient


def test_seeded_accounts_can_login(client: TestClient) -> None:
    for username, password in [("admin", "admin123"), ("teacher", "teacher123"), ("student", "student123")]:
        response = client.post("/api/auth/login", json={"username": username, "password": password})
        assert response.status_code == 200
        payload = response.json()
        assert payload["token"]
        assert payload["user"]["username"] == username


def test_student_can_self_register(client: TestClient) -> None:
    response = client.post(
        "/api/auth/register",
        json={
            "username": "newstudent",
            "full_name": "Новый Студент",
            "password": "student456",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["token"]
    assert payload["user"]["username"] == "newstudent"
    assert payload["user"]["role"] == "student"

    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {payload['token']}"})
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "newstudent"


def test_admin_can_crud_user(client: TestClient, auth_headers) -> None:
    headers = auth_headers("admin", "admin123")

    create_response = client.post(
        "/api/users",
        headers=headers,
        json={
            "username": "student2",
            "full_name": "Второй студент",
            "password": "student234",
            "role": "student",
            "is_active": True,
        },
    )
    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["username"] == "student2"

    list_response = client.get("/api/users", headers=headers)
    assert list_response.status_code == 200
    usernames = [item["username"] for item in list_response.json()]
    assert "student2" in usernames

    update_response = client.put(
        f"/api/users/{created_user['id']}",
        headers=headers,
        json={"full_name": "Студент Обновленный", "role": "teacher", "is_active": True},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "teacher"

    delete_response = client.delete(f"/api/users/{created_user['id']}", headers=headers)
    assert delete_response.status_code == 204


def test_teacher_can_create_and_publish_test(client: TestClient, auth_headers) -> None:
    headers = auth_headers("teacher", "teacher123")
    payload = {
        "title": "Проверка по FastAPI",
        "description": "Минимальный тест по backend-разработке.",
        "is_published": False,
        "questions": [
            {
                "prompt": "Какой фреймворк используется в проекте?",
                "explanation": "Нужен базовый факт о системе.",
                "options": [
                    {"text": "FastAPI", "is_correct": True},
                    {"text": "Django", "is_correct": False},
                ],
            }
        ],
    }

    create_response = client.post("/api/tests", headers=headers, json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["title"] == payload["title"]
    assert len(created["questions"]) == 1

    publish_response = client.post(
        f"/api/tests/{created['id']}/publish",
        headers=headers,
        json={"is_published": True},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["is_published"] is True

    delete_response = client.delete(f"/api/tests/{created['id']}", headers=headers)
    assert delete_response.status_code == 204


def test_student_can_take_published_test(client: TestClient, auth_headers) -> None:
    teacher_headers = auth_headers("teacher", "teacher123")
    student_headers = auth_headers("student", "student123")

    teacher_tests_response = client.get("/api/tests", headers=teacher_headers)
    assert teacher_tests_response.status_code == 200
    teacher_tests = teacher_tests_response.json()
    published_teacher_test = next(test for test in teacher_tests if test["is_published"])
    test_id = published_teacher_test["id"]

    detail_response = client.get(f"/api/tests/{test_id}", headers=student_headers)
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["questions"][0]["options"][0]["is_correct"] is None

    answers = []
    for question in detail["questions"]:
        answers.append({"question_id": question["id"], "option_id": question["options"][0]["id"]})

    submit_response = client.post(
        f"/api/tests/{test_id}/submit",
        headers=student_headers,
        json={"answers": answers},
    )
    assert submit_response.status_code == 200
    result = submit_response.json()
    assert result["total_questions"] == len(detail["questions"])

    attempts_response = client.get("/api/attempts/me", headers=student_headers)
    assert attempts_response.status_code == 200
    assert attempts_response.json()

    forbidden_response = client.post(
        "/api/tests",
        headers=student_headers,
        json={
            "title": "Нельзя",
            "description": "Студент не должен это создавать.",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Вопрос для проверки запрета",
                    "explanation": "",
                    "options": [
                        {"text": "Да", "is_correct": True},
                        {"text": "Нет", "is_correct": False},
                    ],
                }
            ],
        },
    )
    assert forbidden_response.status_code == 403

    teacher_attempts = client.get(f"/api/tests/{test_id}/attempts", headers=teacher_headers)
    assert teacher_attempts.status_code == 200
    assert teacher_attempts.json()


def test_student_cannot_access_unpublished_test(client: TestClient, auth_headers) -> None:
    teacher_headers = auth_headers("teacher", "teacher123")
    student_headers = auth_headers("student", "student123")

    draft_response = client.post(
        "/api/tests",
        headers=teacher_headers,
        json={
            "title": "Скрытый тест",
            "description": "Черновик для проверки прав доступа.",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Что скрыто от студента?",
                    "explanation": "",
                    "options": [
                        {"text": "Черновик", "is_correct": True},
                        {"text": "Публикация", "is_correct": False},
                    ],
                }
            ],
        },
    )
    assert draft_response.status_code == 201
    draft_id = draft_response.json()["id"]

    student_response = client.get(f"/api/tests/{draft_id}", headers=student_headers)
    assert student_response.status_code == 403
