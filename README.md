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
│   └── requirements.txt
├── frontend/                # Заглушка интерфейса Норникеля
│   ├── index.html
│   ├── css/
│   │   └── nornikel-theme.css
│   └── js/
│       └── app.js
└── README.md
```

## Возможности

1. **Валидация целей** — проверка на SMART, отсутствие расплывчатых формулировок, наличие Key Results
2. **Декомпозиция** — разбивка цели компании → команды → индивидуальные задачи
3. **Матчинг** — назначение задач сотрудникам на основе hard/soft skills

## Запуск

### Backend

```bash
cd ai-agent/backend

# Создать виртуальное окружение (рекомендуется)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или: venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
uvicorn app.main:app --reload --port 8000
```

API будет доступен по адресу: http://localhost:8000

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Frontend

Фронтенд — статические HTML/CSS/JS. Можно открыть напрямую:

```bash
# Способ 1: просто открыть файл в браузере
cd ai-agent/frontend
# Открыть index.html двойным кликом

# Способ 2: через Python HTTP-сервер
cd ai-agent/frontend
python -m http.server 8080
# Открыть http://localhost:8080
```

> **Примечание:** Если backend не запущен, фронтенд автоматически переключается на демо-режим (mock-данные).

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

## Интеграция с Qwen (будущее)

В текущей версии логика агента реализована на правилах (rule-based). Для подключения Qwen:

1. Установить `openai` или `transformers`
2. В `validator.py`, `decomposer.py`, `matcher.py` заменить rule-based логику на вызовы LLM
3. Использовать промпты из `backend/app/agent/prompts/` (создать при интеграции)

Пример промпта для валидации:
```
Ты — эксперт по OKR в крупной металлургической компании.
Проверь следующую цель на соответствие критериям SMART.
Укажи конкретные проблемы и дай рекомендации по улучшению.

Цель: {goal}
Key Results: {key_results}
```

## Лицензия

Внутренний проект для Норникель.
