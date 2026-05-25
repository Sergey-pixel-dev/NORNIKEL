"""
Модуль матчинга задач и сотрудников.
Подбирает исполнителей на основе hard skills, soft skills и загрузки.
"""

from typing import List, Dict
from app.models import MatchResult, Assignment, Task, Employee


# Карта соответствия типов задач и навыков
TASK_SKILL_MAP = {
    "ml": ["python", "machine-learning", "data-analysis", "ml", "tensorflow", "pytorch"],
    "frontend": ["javascript", "react", "vue", "angular", "html", "css", "ui"],
    "backend": ["java", "spring", "python", "backend", "api", "microservices"],
    "data": ["sql", "bi", "reporting", "etl", "data-warehouse"],
    "devops": ["docker", "kubernetes", "ci/cd", "aws", "azure"],
    "management": ["teamlead", "agile", "scrum", "планирование"]
}


def detect_task_type(task_text: str, task_type: str) -> str:
    """Определяет тип задачи по тексту и бейджу."""
    text_lower = task_text.lower()
    type_lower = task_type.lower()

    # Сначала проверяем явный тип из бейджа
    for mapped_type in TASK_SKILL_MAP:
        if mapped_type in type_lower:
            return mapped_type

    # Затем анализируем текст
    for mapped_type, keywords in TASK_SKILL_MAP.items():
        if any(kw in text_lower for kw in keywords):
            return mapped_type

    return "general"


def calculate_skill_match(employee: Employee, task_type: str) -> float:
    """Вычисляет степень соответствия навыков сотрудника задаче."""
    required_skills = TASK_SKILL_MAP.get(task_type, [])
    if not required_skills:
        return 0.5

    employee_skills_lower = [s.lower() for s in employee.skills]
    matches = sum(1 for rs in required_skills if any(rs in es for es in employee_skills_lower))
    return matches / len(required_skills)


def calculate_soft_skill_bonus(employee: Employee, task_text: str) -> float:
    """Добавляет бонус за soft skills, если задача требует коммуникации/лидерства."""
    text_lower = task_text.lower()
    bonus = 0.0

    communication_keywords = ["презентация", "отчёт", "документация", "обучение", "внедрение"]
    leadership_keywords = ["руководство", "координация", "управление", "планирование"]

    employee_skills_lower = [s.lower() for s in employee.skills]

    if any(kw in text_lower for kw in communication_keywords):
        if any(s in ["коммуникация", "переговоры", "документация"] for s in employee_skills_lower):
            bonus += 0.15

    if any(kw in text_lower for kw in leadership_keywords):
        if any(s in ["лидерство", "teamlead", "scrum", "agile"] for s in employee_skills_lower):
            bonus += 0.15

    return bonus


def match_employees_to_tasks(tasks: List[Task], employees: List[Employee]) -> MatchResult:
    """
    Распределяет задачи между сотрудниками на основе:
    1. Hard skills (коэффициент 0.6)
    2. Soft skills (коэффициент 0.2)
    3. Балансировка загрузки (коэффициент 0.2)
    """
    assignments = []
    employee_loads: Dict[str, int] = {e.name: 0 for e in employees}

    for task in tasks:
        task_type = detect_task_type(task.text, task.type)
        best_employee = None
        best_score = -1.0

        for employee in employees:
            # Hard skills match (60%)
            hard_match = calculate_skill_match(employee, task_type)

            # Soft skills bonus (20%)
            soft_bonus = calculate_soft_skill_bonus(employee, task.text)

            # Load balancing penalty (20%) - prefer less loaded employees
            load_penalty = employee_loads[employee.name] * 0.1

            total_score = hard_match * 0.6 + soft_bonus * 0.2 - load_penalty * 0.2

            if total_score > best_score:
                best_score = total_score
                best_employee = employee

        if best_employee:
            employee_loads[best_employee.name] += 1

            # Формируем обоснование
            hard_skills = [s for s in best_employee.skills
                          if any(ts in s.lower() for ts in TASK_SKILL_MAP.get(task_type, []))]
            reason = f"Hard skills: {', '.join(hard_skills[:2]) if hard_skills else 'общая компетентность'}"
            if best_score > 0.7:
                reason += ", высокая совместимость"

            assignments.append(Assignment(
                task=task.text,
                employee=best_employee.name,
                reason=reason
            ))

    # Рассчитываем общую уверенность
    if assignments:
        avg_confidence = int(sum(
            calculate_skill_match(
                next(e for e in employees if e.name == a.employee),
                detect_task_type(a.task, "")
            ) for a in assignments
        ) / len(assignments) * 100)
    else:
        avg_confidence = 0

    return MatchResult(
        assignments=assignments,
        confidence=min(99, max(50, avg_confidence))
    )
