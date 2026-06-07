from sqlalchemy import select
from app.db.database import AsyncSessionLocal
from app.db.models import Team, Employee, User
from app.services.auth import hash_password


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
        "team_idx": 1,
        "user_email": "petrov@nornik.ru",
        "user_role": "dept_head",
    },
    {
        "name": "Иванова К.М.",
        "role": "Frontend-разработчик",
        "skills": ["React", "JS", "UI/UX", "TypeScript", "Figma"],
        "projects_history": ["Дашборд КПЭ", "Портал сотрудника"],
        "team_idx": 0,
        "user_email": "ivanova@nornik.ru",
        "user_role": "employee",
    },
    {
        "name": "Сидоров Д.В.",
        "role": "Team Lead / Backend",
        "skills": ["Java", "Spring", "Microservices", "PostgreSQL", "Kafka"],
        "projects_history": ["Микросервисная платформа учёта", "Интеграция с SAP"],
        "team_idx": 0,
        "user_email": "sidorov@nornik.ru",
        "user_role": "dept_head",
    },
    {
        "name": "Козлова А.Р.",
        "role": "BI-аналитик",
        "skills": ["SQL", "Power BI", "ETL", "DWH", "Коммуникация"],
        "projects_history": ["Консолидированная отчётность МСФО", "Анализ EBITDA по дивизионам"],
        "team_idx": 1,
        "user_email": "kozlova@nornik.ru",
        "user_role": "employee",
    },
    {
        "name": "Новиков А.П.",
        "role": "DevOps-инженер",
        "skills": ["Docker", "Kubernetes", "CI/CD", "AWS", "Terraform"],
        "projects_history": ["Миграция в облако", "GitOps для production"],
        "team_idx": 2,
        "user_email": "novikov@nornik.ru",
        "user_role": "employee",
    },
    {
        "name": "Смирнова Е.В.",
        "role": "HR / Change manager",
        "skills": ["Change management", "Тренинги", "Agile", "Коммуникация", "Лидерство"],
        "projects_history": ["Внедрение Agile в дивизионах", "Программа адаптации ИТ-специалистов"],
        "team_idx": 3,
        "user_email": "smirnova@nornik.ru",
        "user_role": "employee",
    },
]

SPECIAL_USERS = [
    {
        "email": "director@nornik.ru",
        "password": "password",
        "name": "Директор Направления",
        "role": "director",
        "employee": {
            "name": "Директор Направления",
            "role": "Руководитель направления",
            "skills": ["Стратегия", "Управление", "Лидерство"],
            "projects_history": ["Цифровая трансформация"],
            "team_idx": None,
        },
    },
]


async def seed_data():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("[seed] Users already exist, skipping seed.")
            return

        # Создаём команды, если их нет
        result = await db.execute(select(Team).limit(1))
        if not result.scalar_one_or_none():
            team_objs = []
            for t in SEED_TEAMS:
                team = Team(**t)
                db.add(team)
                team_objs.append(team)
            await db.commit()
            for t in team_objs:
                await db.refresh(t)
        else:
            team_objs = list((await db.execute(select(Team).order_by(Team.name))).scalars().all())
            # Отсортируем по порядку SEED_TEAMS
            team_map = {t.name: t for t in team_objs}
            team_objs = [team_map[t["name"]] for t in SEED_TEAMS]

        # Создаём специальных пользователей (director)
        emp_to_manager = {}
        for su in SPECIAL_USERS:
            user = User(
                email=su["email"],
                password_hash=hash_password(su["password"]),
                name=su["name"],
                role=su["role"],
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            emp_data = su["employee"]
            team_id = team_objs[emp_data["team_idx"]].id if emp_data["team_idx"] is not None else None
            emp = Employee(
                user_id=user.id,
                name=emp_data["name"],
                role=emp_data["role"],
                skills=emp_data["skills"],
                projects_history=emp_data["projects_history"],
                team_id=team_id,
            )
            db.add(emp)
            await db.commit()
            await db.refresh(emp)
            emp_to_manager[user.id] = emp.id

        # Создаём users и employees из seed
        for e in SEED_EMPLOYEES:
            user = User(
                email=e["user_email"],
                password_hash=hash_password("password"),
                name=e["name"],
                role=e["user_role"],
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

            emp = Employee(
                user_id=user.id,
                name=e["name"],
                role=e["role"],
                skills=e["skills"],
                projects_history=e["projects_history"],
                team_id=team_objs[e["team_idx"]].id,
            )
            db.add(emp)
            await db.commit()
            await db.refresh(emp)
            emp_to_manager[user.id] = emp.id

        # Назначаем руководителей команд
        # Сидоров Д.В. -> Цифровизация процессов (team 0)
        # Петров С.А. -> Данные и аналитика (team 1)
        sidorov_user = await db.execute(select(User).where(User.email == "sidorov@nornik.ru"))
        sidorov_user = sidorov_user.scalar_one_or_none()
        if sidorov_user:
            sidorov_emp = await db.execute(select(Employee).where(Employee.user_id == sidorov_user.id))
            sidorov_emp = sidorov_emp.scalar_one_or_none()
            if sidorov_emp:
                team_objs[0].manager_id = sidorov_emp.id

        petrov_user = await db.execute(select(User).where(User.email == "petrov@nornik.ru"))
        petrov_user = petrov_user.scalar_one_or_none()
        if petrov_user:
            petrov_emp = await db.execute(select(Employee).where(Employee.user_id == petrov_user.id))
            petrov_emp = petrov_emp.scalar_one_or_none()
            if petrov_emp:
                team_objs[1].manager_id = petrov_emp.id

        await db.commit()
        print(f"[seed] Inserted users, linked employees, set team managers.")
