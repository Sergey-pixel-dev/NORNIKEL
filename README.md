# Nornikel OKR AI Agent

ИИ-ассистент для работы с целями и ключевыми результатами (OKR/KPI) в стиле интерфейса Норникеля.

## Структура проекта

```
ai-agent/
├── backend/                 # FastAPI + SQLAlchemy async + PostgreSQL
│   ├── app/
│   │   ├── agent/           # Логика ИИ-агента
│   │   │   ├── validator.py         # Валидация целей (SMART)
│   │   │   ├── decomposer.py        # Декомпозиция по уровням
│   │   │   ├── matcher.py           # Матчинг сотрудников ↔ задачи
│   │   │   ├── ollama_client.py     # HTTP-клиент для Ollama
│   │   │   ├── ai_service.py        # Единый AI-сервис с fallback
│   │   │   ├── ai_mock.py           # Mock-реализации при недоступности LLM
│   │   │   ├── title_generator.py   # Генерация заголовков
│   │   │   └── document_parser.py   # Извлечение текста из PDF/DOCX
│   │   ├── api/
│   │   │   └── routes.py    # REST API endpoints
│   │   ├── crud/
│   │   │   └── goals.py     # CRUD операции
│   │   ├── db/
│   │   │   ├── models.py    # SQLAlchemy модели
│   │   │   ├── database.py  # Подключение к PostgreSQL
│   │   │   └── seed.py      # Сид-данные
│   │   ├── schemas.py       # Pydantic модели
│   │   └── main.py          # Точка входа FastAPI
│   ├── alembic/             # Миграции
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/                # Vanilla JS + CSS, Nginx
│   ├── index.html
│   ├── css/
│   │   └── nornikel-theme.css
│   ├── js/
│   │   └── app.js
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
├── Makefile
└── README.md
```

## Возможности

1. **Валидация целей** — проверка на SMART, оценка по 6 критериям, рекомендации
2. **AI-переписывание** — LLM переписывает цель в формат SMART и генерирует Key Results
3. **Декомпозиция** — разбивка цели компании → задачи команд (динамическое число команд из БД)
4. **Team Breakdown** — разбиение задачи одной команды на 3–5 конкретных подзадач с технологиями
5. **Матчинг** — ручное и ИИ-распределение задач по сотрудникам с учётом навыков
6. **Версионирование** — автоматические снапшоты на каждом шаге, откат к предыдущей версии
7. **Контекстный чат** — история сообщений с LLM сохраняется в БД, можно сбросить
8. **Загрузка документов** — извлечение текста из PDF/DOCX для дальнейшей обработки

## Запуск через Docker

### Требования

- Docker 20.10+
- Docker Compose 2.0+
- Ollama с моделью `phi4-mini:latest` (или настройте `OLLAMA_MODEL`)

### Быстрый старт

```bash
cd ai-agent

# Собрать и запустить
docker compose up --build -d
```

После запуска:

| Сервис | URL | Описание |
|--------|-----|----------|
| Frontend | http://localhost:8082 | Интерфейс Норникеля + ИИ-ассистент |
| Backend API | http://localhost:8000 | REST API |
| Swagger UI | http://localhost:8000/docs | Документация API |

### Остановка

```bash
# Остановить контейнеры
docker compose down

# Остановить и удалить volumes (вместе с данными БД)
docker compose down -v
```

### Пересборка

```bash
# Полная пересборка
docker compose up --build --force-recreate
```

### Просмотр логов

```bash
# Все контейнеры
docker compose logs -f

# Только backend
docker compose logs -f backend
```

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/validate` | Проверить цель на SMART, создать цель в БД |
| POST | `/api/ai-rewrite` | Переписать цель при помощи ИИ |
| POST | `/api/upload-document` | Загрузить PDF/DOCX, извлечь текст |
| GET | `/api/goals` | Список целей |
| GET | `/api/goals/{id}` | Детали цели (с декомпозициями, задачами, версиями) |
| POST | `/api/goals/{id}/decompose` | Декомпозировать цель на команды |
| POST | `/api/goals/{id}/generate-tasks` | Сгенерировать задачи из декомпозиции |
| POST | `/api/goals/{id}/breakdown-team` | Разбить задачу команды на подзадачи |
| POST | `/api/goals/{id}/suggest-assignments` | ИИ предлагает назначения |
| POST | `/api/goals/{id}/assign` | Сохранить назначения |
| POST | `/api/goals/{id}/rollback` | Откат к версии |
| POST | `/api/goals/{id}/reset-chat` | Очистить контекст ИИ |
| GET | `/api/teams` | Список команд |
| GET | `/api/employees` | Список сотрудников |
| GET | `/api/teams/{id}/employees` | Сотрудники конкретной команды |
| GET | `/api/goals/{id}/tasks` | Задачи цели |
| POST/PUT/DELETE | `/api/tasks` | CRUD задач |

## Архитектура

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│ Пользователь │─────▶│  Frontend   │─────▶│   Backend   │
│  (браузер)   │      │  (nginx)    │      │  (FastAPI)  │
└─────────────┘      └─────────────┘      └─────────────┘
                                                │
                    ┌───────────────────────────┼───────────┐
                    ▼                           ▼           ▼
              ┌──────────┐            ┌────────────┐  ┌────────────┐
              │Validator │            │Decomposer  │  │Matcher     │
              │(SMART)   │            │(каскад)    │  │(skills)    │
              └──────────┘            └────────────┘  └────────────┘
                    │
                    ▼
              ┌─────────────────────────────────────┐
              │  Ollama (phi4-mini:latest)          │
              │  host.docker.internal:11434          │
              └─────────────────────────────────────┘
```

## Git

```bash
# Просмотр истории
git log --oneline

# Статус
git status
```

## Лицензия

Внутренний проект для Норникель.
