from __future__ import annotations

import sqlite3

from . import services


def seed_demo_data(connection: sqlite3.Connection) -> None:
    user_count = connection.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if user_count:
        return

    services.create_user(
        connection,
        username="admin",
        full_name="Системный администратор",
        password="admin123",
        role="admin",
        is_active=True,
    )
    teacher = services.create_user(
        connection,
        username="teacher",
        full_name="Мария Преподаватель",
        password="teacher123",
        role="teacher",
        is_active=True,
    )
    services.create_user(
        connection,
        username="student",
        full_name="Иван Студент",
        password="student123",
        role="student",
        is_active=True,
    )

    services.create_test(
        connection,
        owner_id=teacher["id"],
        payload={
            "title": "Основы Git",
            "description": "Короткий тест по базовым понятиям Git.",
            "is_published": True,
            "questions": [
                {
                    "prompt": "Какая команда показывает состояние репозитория?",
                    "explanation": "Команда status отображает состояние файлов.",
                    "options": [
                        {"text": "git status", "is_correct": True},
                        {"text": "git show-tree", "is_correct": False},
                        {"text": "git ping", "is_correct": False},
                    ],
                },
                {
                    "prompt": "Что делает команда git add?",
                    "explanation": "Она подготавливает изменения к коммиту.",
                    "options": [
                        {"text": "Удаляет ветку", "is_correct": False},
                        {"text": "Добавляет изменения в индекс", "is_correct": True},
                        {"text": "Публикует код в облако", "is_correct": False},
                    ],
                },
            ],
        },
    )
    services.create_test(
        connection,
        owner_id=teacher["id"],
        payload={
            "title": "Принципы Twelve-Factor App",
            "description": "Черновой тест для внутреннего редактирования.",
            "is_published": False,
            "questions": [
                {
                    "prompt": "Что рекомендуется выносить в переменные окружения?",
                    "explanation": "Конфигурация не должна быть жестко зашита в коде.",
                    "options": [
                        {"text": "Конфигурацию", "is_correct": True},
                        {"text": "HTML-разметку", "is_correct": False},
                        {"text": "SQL-запросы как константы интерфейса", "is_correct": False},
                    ],
                }
            ],
        },
    )
