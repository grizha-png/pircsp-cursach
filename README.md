# Interactive Educational Tests Constructor

Курсовой fullstack-проект по теме **«Интерактивный конструктор образовательных тестов»**.

Система реализует:

- анализ предметной области и проектные артефакты в `docs/`;
- клиент-серверную архитектуру;
- FastAPI backend с CRUD-операциями;
- авторизацию и аутентификацию;
- ролевую модель `admin / teacher / student`;
- работу с базой данных SQLite;
- тестовые данные;
- Dockerfile и `docker-compose`;
- артефакты по фаззингу и облачному развертыванию.

## Структура проекта

- `docs/` — аналитика, UML, гайды по фаззингу и облакам, черновик презентации.
- `src/` — backend-приложение на FastAPI.
- `frontend/` — клиентское приложение на HTML/CSS/JavaScript.
- `tests/` — автоматические тесты API и негативные/фаззинг-проверки.
- `data/` — файл SQLite базы данных при локальном запуске.

## Функциональность

- вход в систему по логину и паролю;
- управление пользователями администратором;
- создание, редактирование, публикация и удаление тестов преподавателем;
- прохождение опубликованных тестов студентом;
- автоматический подсчет результата;
- просмотр истории попыток;
- просмотр результатов прохождения по тесту для преподавателя.

## Тестовые учетные записи

- `admin / admin123`
- `teacher / teacher123`
- `student / student123`

## Подготовка `.env`

В проекте используется локальный файл `.env` в корне репозитория.

- для Docker Compose переменные передаются сервисам через `env_file: .env`;
- для локального запуска backend приложение также читает `.env` автоматически;
- в GitHub следует отправлять `.env.example`, а не реальный `.env`.

Если нужно пересоздать файл:

```bash
cp .env.example .env
```

## Локальный запуск backend

Из корня проекта:

```bash
PYTHONPATH=src uvicorn app.main:app --reload
```

Backend будет доступен на `http://127.0.0.1:8000`.

## Локальный запуск frontend

Самый простой вариант:

```bash
python3 -m http.server 8080 --directory frontend
```

Frontend будет доступен на `http://127.0.0.1:8080`.

При таком запуске клиент автоматически обращается к backend по адресу `http://127.0.0.1:8000/api`, поэтому backend должен быть запущен отдельно.

Если frontend раздается через `frontend/nginx.conf` в Docker-сценарии, запросы также могут идти через reverse proxy по пути `/api`.

## Запуск через Docker Compose

Из корня проекта:

```bash
docker compose up -d --build
```

После запуска:

- frontend: `http://127.0.0.1:8080`
- backend: `http://127.0.0.1:8000`
- health-check: `http://127.0.0.1:8000/api/health`

## Запуск тестов

```bash
pytest
```

Для запуска только фаззинг-набора:

```bash
pytest tests/test_fuzzing.py
```

## Основные API-маршруты

- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/users`
- `POST /api/users`
- `PUT /api/users/{user_id}`
- `DELETE /api/users/{user_id}`
- `GET /api/tests`
- `GET /api/tests/{test_id}`
- `POST /api/tests`
- `PUT /api/tests/{test_id}`
- `DELETE /api/tests/{test_id}`
- `POST /api/tests/{test_id}/publish`
- `POST /api/tests/{test_id}/submit`
- `GET /api/attempts/me`
- `GET /api/tests/{test_id}/attempts`

## Документация

- [Анализ предметной области](./docs/01-domain-analysis.md)
- [Выбор архитектуры](./docs/02-architecture.md)
- [Выбор стека](./docs/03-tech-stack.md)
- [Гайд по фаззингу](./docs/04-fuzzing-guide.md)
- [Облачное развертывание](./docs/05-cloud-deployment-guide.md)
- [Черновик презентации](./docs/06-presentation-outline.md)

## UML

- [Use Case](./docs/uml/use-case.uml)
- [Component](./docs/uml/component.uml)
- [Domain/Class](./docs/uml/class-domain.uml)
- [Sequence Auth](./docs/uml/sequence-auth.uml)
- [Deployment](./docs/uml/deployment.uml)
