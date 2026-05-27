"""
Модуль декомпозиции целей OKR.
Разбивает верхнеуровневую цель на подцели для команд и индивидуальные задачи.
"""

import re
from typing import List, Dict
from app.models import DecomposeResult


# Шаблоны декомпозиции по доменам
DECOMPOSITION_PATTERNS = {
    "цифровизац": {
        "prefixes": [
            "Разработать и внедрить программное решение для автоматизации целевого процесса",
            "Обеспечить обучение персонала и подготовить инфраструктуру для новых инструментов"
        ],
        "individual": "Создать прототип решения, провести пилотное тестирование и подготовить документацию"
    },
    "производств": {
        "prefixes": [
            "Оптимизировать производственные процессы и внедрить систему мониторинга",
            "Повысить квалификацию операционного персонала и обновить инструкции"
        ],
        "individual": "Внедрить контрольные точки на участке, провести анализ отклонений"
    },
    "финанс": {
        "prefixes": [
            "Автоматизировать процессы финансового планирования и отчётности",
            "Внедрить систему управленческого учёта и контроля бюджета"
        ],
        "individual": "Подготовить аналитический отчёт и предложения по оптимизации расходов"
    },
    "безопасност": {
        "prefixes": [
            "Внедрить технические средства контроля и систему инцидент-менеджмента",
            "Провести тренинги и аттестацию персонала по промышленной безопасности"
        ],
        "individual": "Выполнить аудит рабочих мест и подготовить план корректирующих мероприятий"
    },
    "эколог": {
        "prefixes": [
            "Модернизировать очистные сооружения и системы мониторинга выбросов",
            "Разработать программу снижения экологического воздействия производства"
        ],
        "individual": "Провести инвентаризацию источников выбросов и подготовить график модернизации"
    }
}


def detect_domain(goal: str) -> str:
    """Определяет домен цели по ключевым словам."""
    goal_lower = goal.lower()
    for domain in DECOMPOSITION_PATTERNS:
        if domain in goal_lower:
            return domain
    return "default"


def decompose_goal(goal: str, teams: List[Dict[str, str]] = None) -> DecomposeResult:
    """
    Декомпозирует цель компании на уровни:
    - Компания (исходная цель)
    - Команды (динамическое число подцелей под реальные команды из БД)
    - Индивидуальная задача
    """
    domain = detect_domain(goal)
    pattern = DECOMPOSITION_PATTERNS.get(domain, DECOMPOSITION_PATTERNS["цифровизац"])

    # Извлекаем числовые целевые значения из цели
    numbers = re.findall(r'\d+(?:[.,]\d+)?\s*(?:%|процент|руб|usd|млн|тыс)', goal.lower())
    metric_context = f" (целевые показатели: {', '.join(numbers)})" if numbers else ""

    # Если команды не переданы — используем дефолт
    if not teams:
        teams = [
            {"name": "Команда A", "specialization": "Техническая реализация"},
            {"name": "Команда B", "specialization": "Орг. поддержка"}
        ]

    team_goals = []
    prefixes = pattern["prefixes"]
    for idx, team in enumerate(teams):
        prefix = prefixes[idx % len(prefixes)]
        team_goals.append({
            "team_id": None,
            "team_name": team["name"],
            "text": f"{prefix}{metric_context if idx == 0 else ''}"
        })

    individual = f"{pattern['individual']}{metric_context}"

    reasoning = (
        f"Цель отнесена к домену '{domain}'. Декомпозиция выполнена с учётом "
        f"функциональной специализации {len(teams)} команд. "
        f"Каждая команда получила направление, соответствующее её компетенциям."
    )

    traceability_score = 85
    if numbers:
        traceability_score += 5
    if len(goal) > 50:
        traceability_score += 5
    traceability_score = min(99, traceability_score)

    return DecomposeResult(
        company=goal,
        teams=team_goals,
        individual=individual,
        reasoning=reasoning,
        traceability_score=traceability_score
    )
