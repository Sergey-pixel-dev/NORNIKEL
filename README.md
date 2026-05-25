# 🤖 Nornikel OKR AI Agent

ИИ-ассистент для работы с целями и ключевыми результатами (OKR/KPI) в стиле интерфейса Норникеля.

## Структура проекта

```
ai-agent/
├── backend/                 # FastAPI + Python
│   ├── app/
│   │   ├── agent/           # Логика ИИ-агента
│   │   │   ├── validator.py # Валидация целей (SMART)
│   │   │   ├── decomposer.py# Декомпозиция по уровням
│   │   │   └── matcher.py   # Матчинг сотрудников ↔ задачи
│   │   ├── api/
│   │   │   └── routes.py    # REST API endpoints
│   │   ├── models.py        # Pydantic модели
│   │   └── main.py          # Точка входа FastAPI
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/                # Заглушка интерфейса Норникеля
│   ├── index.html
│   ├── css/
│   │   └── nornikel-theme.css
│   ├── js/
│   │   └── app.js
│   ├── Dockerfile
│   ├── .dockerignore
│   └── nginx.conf
├── docker-compose.yml
├── .gitignore
└── README.md
```

## Возможности

1. **Валидация целей** — проверка на SMART, отсутствие расплывчатых формулировок, наличие Key Results
2. **Декомпозиция** — разбивка цели компании → команды → индивидуальные задачи
3. **Матчинг** — назначение задач сотрудникам на основе hard/soft skills

## Запуск через Docker

### Требования

- Docker 20.10+
- Docker Compose 2.0+

### Быстрый старт

```bash
cd ai-agent

# Собрать и запустить
docker compose up --build

# Или в фоне
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

# Остановить и удалить volumes
docker compose down -v
```

### Пересборка

```bash
# Полная пересборка
docker compose up --build --force-recreate

# Пересборка только backend
docker compose up --build backend

# Пересборка только frontend
docker compose up --build frontend
```

### Просмотр логов

```bash
# Все контейнеры
docker compose logs -f

# Только backend
docker compose logs -f backend

# Только frontend
docker compose logs -f frontend
```

## API Endpoints

| Метод | Endpoint | Описание |
|-------|----------|----------|
| POST | `/api/validate` | Проверить цель на SMART |
| POST | `/api/decompose` | Декомпозировать цель |
| POST | `/api/match` | Подобрать исполнителей |

### Примеры запросов

**Валидация цели:**
```bash
curl -X POST http://localhost:8000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Сократить время обработки заказов на 20% до конца Q3 2025",
    "key_results": [
      "Внедрить автоматизацию 3 процессов",
      "Снизить ошибки в заказах до 1%"
    ]
  }'
```

**Декомпозиция:**
```bash
curl -X POST http://localhost:8000/api/decompose \
  -H "Content-Type: application/json" \
  -d '{"goal": "Цифровизация процесса учёта сырья"}'
```

**Матчинг:**
```bash
curl -X POST http://localhost:8000/api/match \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"text": "Разработка модели", "type": "ML"},
      {"text": "Создание интерфейса", "type": "Frontend"}
    ],
    "employees": [
      {"name": "Иванов", "role": "DS", "skills": ["python", "ml"]},
      {"name": "Петров", "role": "Dev", "skills": ["react", "js"]}
    ]
  }'
```

## Архитектура

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Пользователь   │─────▶│  Frontend   │─────▶│   Backend   │
│  (браузер)       │      │  (nginx)    │      │  (FastAPI)  │
└─────────────┘      └─────────────┘      └─────────────┘
                                                │
                    ┌───────────────────────────┼───────────┐
                    ▼                           ▼           ▼
              ┌──────────┐            ┌────────────┐  ┌────────────┐
              │Validator │            │Decomposer  │  │Matcher     │
              │(SMART)   │            │(каскад)    │  │(skills)    │
              └──────────┘            └────────────┘  └────────────┘
```

## Интеграция с Qwen (будущее)

В текущей версии логика агента реализована на правилах (rule-based). Для подключения Qwen:

1. Добавить в `backend/requirements.txt`:
   ```
   openai>=1.0
   # или
   transformers>=4.35
   ```

2. В `backend/app/agent/` создать модуль `llm_client.py` для вызовов Qwen

3. Заменить rule-based логику в `validator.py`, `decomposer.py`, `matcher.py` на LLM-промпты

Пример промпта для валидации:
```
Ты — эксперт по OKR в крупной металлургической компании.
Проверь следующую цель на соответствие критериям SMART.
Укажи конкретные проблемы и дай рекомендации по улучшению.

Цель: {goal}
Key Results: {key_results}
```

## Git

```bash
# Просмотр истории
cd ai-agent
git log --oneline

# Статус
git status
```

## Лицензия

Внутренний проект для Норникель.
