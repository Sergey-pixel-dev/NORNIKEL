import asyncio
from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Team, Employee


SEED_TEAMS = [
    {
        "name": "Цифровизация процессов",
        "specialization": "Разработка ПО, автоматизация, интеграция",
        "description": "Команда отвечает за цифровую трансформацию производственных и бизнес-процессов.",
    },
    {
        "name": "Данные и аналитика",
        "specialization": "Data Science, BI, машинное обучение",
        "description": "Построение моделей прогнозирования, аналитических дашбордов и отчётности.",
    },
    {
        "name": "Инфраструктура и DevOps",
        "specialization": "Облака, CI/CD, Kubernetes, безопасность",
        "description": "Поддержание инфраструктуры, развёртывание, мониторинг и информационная безопасность.",
    },
    {
        "name": "Орг. развитие и обучение",
        "specialization": "HR, change management, тренинги",
        "description": "Организационная поддержка изменений, обучение персонала, коммуникации.",
    },
]

SEED_EMPLOYEES = [
    {
        "name": "Петров С.А.",
        "role": "Data Scientist",
        "skills": ["Python", "ML", "Аналитика", "SQL", "TensorFlow"],
        "projects_history": ["Прогнозирование отказов оборудования", "Анализ сырьевых потоков"],
    },
    {
        "name": "Иванова К.М.",
        "role": "Frontend-разработчик",
        "skills": ["React", "JS", "UI/UX", "TypeScript", "Figma"],
        "projects_history": ["Дашборд КПЭ", "Портал сотрудника"],
    },
    {
        "name": "Сидоров Д.В.",
        "role": "Team Lead / Backend",
        "skills": ["Java", "Spring", "Microservices", "PostgreSQL", "Kafka"],
        "projects_history": ["Микросервисная платформа учёта", "Интеграция с SAP"],
    },
    {
        "name": "Козлова А.Р.",
        "role": "BI-аналитик",
        "skills": ["SQL", "Power BI", "ETL", "DWH", "Коммуникация"],
        "projects_history": ["Консолидированная отчётность МСФО", "Анализ EBITDA по дивизионам"],
    },
    {
        "name": "Новиков А.П.",
        "role": "DevOps-инженер",
        "skills": ["Docker", "Kubernetes", "CI/CD", "AWS", "Terraform"],
        "projects_history": ["Миграция в облако", "GitOps для production"],
    },
    {
        "name": "Смирнова Е.В.",
        "role": "HR / Change manager",
        "skills": ["Change management", "Тренинги", "Agile", "Коммуникация", "Лидерство"],
        "projects_history": ["Внедрение Agile в дивизионах", "Программа адаптации ИТ-специалистов"],
    },
]


async def seed_data():
    async with AsyncSessionLocal() as db:
        # Проверяем, есть ли уже данные
        result = await db.execute(select(Team).limit(1))
        if result.scalar_one_or_none():
            print("[seed] Teams already exist, skipping seed.")
            return

        for t in SEED_TEAMS:
            db.add(Team(**t))
        for e in SEED_EMPLOYEES:
            db.add(Employee(**e))

        await db.commit()
        print(f"[seed] Inserted {len(SEED_TEAMS)} teams and {len(SEED_EMPLOYEES)} employees.")
