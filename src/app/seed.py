from __future__ import annotations

import sqlite3

from . import services


def _ensure_user(
    connection: sqlite3.Connection,
    *,
    username: str,
    full_name: str,
    password: str,
    role: str,
    is_active: bool = True,
) -> dict:
    existing = services.get_user_by_username(connection, username)
    if existing:
        return services.row_to_user_public(existing)
    return services.create_user(
        connection,
        username=username,
        full_name=full_name,
        password=password,
        role=role,
        is_active=is_active,
    )


def _ensure_test(connection: sqlite3.Connection, owner_id: int, payload: dict) -> int:
    existing = connection.execute(
        "SELECT id FROM tests WHERE owner_id = ? AND title = ?",
        (owner_id, payload["title"]),
    ).fetchone()
    if existing:
        return existing["id"]
    created = services.create_test(connection, payload=payload, owner_id=owner_id)
    return created["id"]


def _build_answers(test_detail: dict, correctness_pattern: list[bool]) -> list[dict]:
    if len(test_detail["questions"]) != len(correctness_pattern):
        raise ValueError("Correctness pattern length must match the number of questions.")

    answers: list[dict] = []
    for question, should_be_correct in zip(test_detail["questions"], correctness_pattern, strict=True):
        if should_be_correct:
            selected_option = next(option for option in question["options"] if option["is_correct"])
        else:
            selected_option = next(option for option in question["options"] if not option["is_correct"])
        answers.append({"question_id": question["id"], "option_id": selected_option["id"]})
    return answers


def _ensure_attempt(connection: sqlite3.Connection, *, test_id: int, student_id: int, correctness_pattern: list[bool]) -> None:
    existing = connection.execute(
        "SELECT 1 FROM attempts WHERE test_id = ? AND user_id = ? LIMIT 1",
        (test_id, student_id),
    ).fetchone()
    if existing:
        return
    test_detail = services.get_test_detail(connection, test_id, include_correct=True)
    answers = _build_answers(test_detail, correctness_pattern)
    services.submit_attempt(connection, test_id=test_id, student_id=student_id, answers=answers)


def seed_demo_data(connection: sqlite3.Connection) -> None:
    admin = _ensure_user(
        connection,
        username="admin",
        full_name="Системный администратор",
        password="admin123",
        role="admin",
    )
    teacher = _ensure_user(
        connection,
        username="teacher",
        full_name="Мария Преподаватель",
        password="teacher123",
        role="teacher",
    )
    teacher_db = _ensure_user(
        connection,
        username="teacher_db",
        full_name="Алексей Базы Данных",
        password="teacherdb123",
        role="teacher",
    )
    teacher_web = _ensure_user(
        connection,
        username="teacher_web",
        full_name="Елена Веб-Технологии",
        password="teacherweb123",
        role="teacher",
    )
    teacher_sec = _ensure_user(
        connection,
        username="teacher_sec",
        full_name="Никита Безопасность",
        password="teachersec123",
        role="teacher",
    )

    student = _ensure_user(
        connection,
        username="student",
        full_name="Иван Студент",
        password="student123",
        role="student",
    )
    student_anna = _ensure_user(
        connection,
        username="student_anna",
        full_name="Анна Смирнова",
        password="studentanna123",
        role="student",
    )
    student_boris = _ensure_user(
        connection,
        username="student_boris",
        full_name="Борис Климов",
        password="studentboris123",
        role="student",
    )
    student_elena = _ensure_user(
        connection,
        username="student_elena",
        full_name="Елена Новикова",
        password="studentelena123",
        role="student",
    )
    student_roman = _ensure_user(
        connection,
        username="student_roman",
        full_name="Роман Егоров",
        password="studentroman123",
        role="student",
    )
    _ensure_user(
        connection,
        username="student_inactive",
        full_name="Архивный Студент",
        password="studentinactive123",
        role="student",
        is_active=False,
    )

    git_test_id = _ensure_test(
        connection,
        owner_id=teacher["id"],
        payload={
            "title": "Основы Git",
            "description": "Короткий тест по базовым понятиям Git и работе с репозиторием.",
            "is_published": True,
            "questions": [
                {
                    "prompt": "Какая команда показывает состояние рабочего каталога и индекса?",
                    "explanation": "Команда git status выводит состояние файлов и staged-изменений.",
                    "options": [
                        {"text": "git status", "is_correct": True},
                        {"text": "git sync", "is_correct": False},
                        {"text": "git repo-check", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Для чего используется команда git add?",
                    "explanation": "Она подготавливает изменения перед созданием коммита.",
                    "options": [
                        {"text": "Удаляет ветку", "is_correct": False},
                        {"text": "Добавляет изменения в индекс", "is_correct": True},
                        {"text": "Публикует репозиторий в облако", "is_correct": False},
                    ],
                },
            ],
        },
    )

    _ensure_test(
        connection,
        owner_id=teacher["id"],
        payload={
            "title": "Принципы Twelve-Factor App",
            "description": "Черновой тест для внутреннего редактирования и демонстрации непубликованного сценария.",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Что рекомендуется выносить в переменные окружения в приложении?",
                    "explanation": "Конфигурацию не следует жестко прописывать в исходном коде.",
                    "options": [
                        {"text": "Конфигурацию", "is_correct": True},
                        {"text": "HTML-разметку клиентского интерфейса", "is_correct": False},
                        {"text": "Комментарии разработчиков", "is_correct": False},
                    ],
                }
            ],
        },
    )

    fastapi_test_id = _ensure_test(
        connection,
        owner_id=teacher["id"],
        payload={
            "title": "FastAPI и REST API",
            "description": "Проверка базовых знаний о FastAPI, HTTP-методах и JSON API.",
            "is_published": True,
            "questions": [
                {
                    "prompt": "Какой HTTP-метод обычно используется для создания новой сущности?",
                    "explanation": "Для создания ресурса в REST чаще всего применяют POST.",
                    "options": [
                        {"text": "POST", "is_correct": True},
                        {"text": "GET", "is_correct": False},
                        {"text": "HEAD", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Что из перечисленного FastAPI предоставляет автоматически?",
                    "explanation": "FastAPI генерирует интерактивную документацию OpenAPI.",
                    "options": [
                        {"text": "Интерактивную документацию API", "is_correct": True},
                        {"text": "GUI для PostgreSQL", "is_correct": False},
                        {"text": "Сборку frontend в Docker", "is_correct": False},
                    ],
                },
                {
                    "prompt": "В каком формате чаще всего обмениваются данными клиент и REST API?",
                    "explanation": "Для API веб-приложений обычно используется JSON.",
                    "options": [
                        {"text": "JSON", "is_correct": True},
                        {"text": "BMP", "is_correct": False},
                        {"text": "DOCX", "is_correct": False},
                    ],
                },
            ],
        },
    )

    sql_test_id = _ensure_test(
        connection,
        owner_id=teacher_db["id"],
        payload={
            "title": "Основы SQL и проектирования БД",
            "description": "Тест по реляционным базам данных, ключам и SQL-запросам.",
            "is_published": True,
            "questions": [
                {
                    "prompt": "Какой ключ однозначно идентифицирует запись в таблице?",
                    "explanation": "Первичный ключ обеспечивает уникальную идентификацию строки.",
                    "options": [
                        {"text": "Первичный ключ", "is_correct": True},
                        {"text": "Внешний ключ", "is_correct": False},
                        {"text": "Индекс", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Какой оператор SQL используется для получения данных из таблицы?",
                    "explanation": "SELECT предназначен для выборки данных.",
                    "options": [
                        {"text": "SELECT", "is_correct": True},
                        {"text": "BUILD", "is_correct": False},
                        {"text": "ATTACH", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Для чего нужен внешний ключ в реляционной базе данных?",
                    "explanation": "Он связывает данные между таблицами и поддерживает ссылочную целостность.",
                    "options": [
                        {"text": "Для связи таблиц", "is_correct": True},
                        {"text": "Для стилизации интерфейса", "is_correct": False},
                        {"text": "Для сжатия JSON", "is_correct": False},
                    ],
                },
            ],
        },
    )

    web_test_id = _ensure_test(
        connection,
        owner_id=teacher_web["id"],
        payload={
            "title": "Web-технологии и HTTP",
            "description": "Вопросы по браузеру, маршрутам, HTTP и клиент-серверному взаимодействию.",
            "is_published": True,
            "questions": [
                {
                    "prompt": "Какой статус-код HTTP означает успешное выполнение запроса?",
                    "explanation": "Код 200 OK сигнализирует об успешной обработке запроса.",
                    "options": [
                        {"text": "200", "is_correct": True},
                        {"text": "404", "is_correct": False},
                        {"text": "500", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Какая часть архитектуры отвечает за отображение интерфейса пользователю?",
                    "explanation": "За пользовательский интерфейс отвечает клиентская часть приложения.",
                    "options": [
                        {"text": "Клиентская часть", "is_correct": True},
                        {"text": "SQL-движок", "is_correct": False},
                        {"text": "Система контроля версий", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Для чего в проекте используется nginx?",
                    "explanation": "Он раздает статику и проксирует обращения к backend API.",
                    "options": [
                        {"text": "Для reverse proxy и статики", "is_correct": True},
                        {"text": "Для хранения пользователей", "is_correct": False},
                        {"text": "Для компиляции Python-кода", "is_correct": False},
                    ],
                },
            ],
        },
    )

    security_test_id = _ensure_test(
        connection,
        owner_id=teacher_sec["id"],
        payload={
            "title": "Роли и безопасность веб-приложений",
            "description": "Тест по RBAC, проверке прав доступа и обработке пользовательских действий.",
            "is_published": True,
            "questions": [
                {
                    "prompt": "Что означает подход RBAC в веб-приложениях?",
                    "explanation": "Доступ к функциям определяется ролью пользователя.",
                    "options": [
                        {"text": "Управление доступом на основе ролей", "is_correct": True},
                        {"text": "Случайный выбор базовых аккаунтов", "is_correct": False},
                        {"text": "Резервное архивирование браузерного кеша", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Где должны проверяться критичные ограничения доступа?",
                    "explanation": "Проверка прав должна выполняться на сервере, а не только в интерфейсе.",
                    "options": [
                        {"text": "На сервере", "is_correct": True},
                        {"text": "Только в CSS", "is_correct": False},
                        {"text": "Только в браузере пользователя", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Какой ответ сервера наиболее уместен при запрете действия по роли?",
                    "explanation": "При нехватке прав обычно возвращается 403 Forbidden.",
                    "options": [
                        {"text": "403 Forbidden", "is_correct": True},
                        {"text": "101 Switching Protocols", "is_correct": False},
                        {"text": "204 No Content", "is_correct": False},
                    ],
                },
            ],
        },
    )

    _ensure_test(
        connection,
        owner_id=teacher_sec["id"],
        payload={
            "title": "Контейнеризация с Docker",
            "description": "Черновой тест для преподавателя по основам контейнеризации и docker-compose.",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Для чего используется Dockerfile в проекте?",
                    "explanation": "Он описывает образ приложения и шаги сборки.",
                    "options": [
                        {"text": "Для описания сборки образа", "is_correct": True},
                        {"text": "Для хранения попыток студентов", "is_correct": False},
                        {"text": "Для замены базы данных", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Что делает docker-compose в многосервисном проекте?",
                    "explanation": "Он помогает запускать и описывать связанные сервисы приложения.",
                    "options": [
                        {"text": "Оркестрирует несколько сервисов", "is_correct": True},
                        {"text": "Шифрует HTML", "is_correct": False},
                        {"text": "Заменяет nginx в браузере", "is_correct": False},
                    ],
                },
            ],
        },
    )

    _ensure_attempt(connection, test_id=git_test_id, student_id=student["id"], correctness_pattern=[True, True])
    _ensure_attempt(connection, test_id=git_test_id, student_id=student_anna["id"], correctness_pattern=[True, False])
    _ensure_attempt(connection, test_id=fastapi_test_id, student_id=student_boris["id"], correctness_pattern=[True, True, False])
    _ensure_attempt(connection, test_id=sql_test_id, student_id=student_elena["id"], correctness_pattern=[True, False, True])
    _ensure_attempt(connection, test_id=web_test_id, student_id=student_roman["id"], correctness_pattern=[False, True, True])
    _ensure_attempt(connection, test_id=security_test_id, student_id=student["id"], correctness_pattern=[True, True, True])
    _ensure_attempt(connection, test_id=security_test_id, student_id=student_boris["id"], correctness_pattern=[True, False, True])

    demo_user = services.get_user_by_username(connection, "demo_user")
    if demo_user:
        _ensure_attempt(connection, test_id=fastapi_test_id, student_id=demo_user["id"], correctness_pattern=[False, True, True])

    # Keep the admin record referenced so the core demo accounts are guaranteed to exist.
    _ = admin
