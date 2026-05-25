FROM python:3.12-slim

# Установка curl для healthcheck и uv для быстрой установки пакетов
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Копирование кода
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
