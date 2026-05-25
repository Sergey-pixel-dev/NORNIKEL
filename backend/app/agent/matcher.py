"""
Модуль матчинга задач и сотрудников.
Подбирает исполнителей на основе hard skills, soft skills и загрузки.
"""

from typing import List, Dict
from app.schemas import MatchResult, AssignmentItem


TASK_SKILL_MAP = {
    "ml": ["python", "machine-learning", "data-analysis", "ml", "tensorflow", "pytorch"],
    "frontend": ["javascript", "react", "vue", "angular", "html", "css", "ui"],
    "backend": ["java", "spring", "python", "backend", "api", "microservices"],
    "data": ["sql", "bi", "reporting", "etl", "data-warehouse"],
    "devops": ["docker", "kubernetes", "ci/cd", "aws", "azure"],
    "management": ["teamlead", "agile", "scrum", "планирование"]
}


def detect_task_type(task_text: str, task_type: str) -> str:
    text_lower = task_text.lower()
    type_lower = task_type.lower()

    for mapped_type in TASK_SKILL_MAP:
        if mapped_type in type_lower:
            return mapped_type

    for mapped_type, keywords in TASK_SKILL_MAP.items():
        if any(kw in text_lower for kw in keywords):
            return mapped_type

    return "general"


def calculate_skill_match(employee: dict, task_type: str) -> float:
    required_skills = TASK_SKILL_MAP.get(task_type, [])
    if not required_skills:
        return 0.5

    employee_skills_lower = [s.lower() for s in employee.get("skills", [])]
    matches = sum(1 for rs in required_skills if any(rs in es for es in employee_skills_lower))
    return matches / len(required_skills)


def calculate_soft_skill_bonus(employee: dict, task_text: str) -> float:
    text_lower = task_text.lower()
    bonus = 0.0

    communication_keywords = ["презентация", "отчёт", "документация", "обучение", "внедрение"]
    leadership_keywords = ["руководство", "координация", "управление", "планирование"]

    employee_skills_lower = [s.lower() for s in employee.get("skills", [])]

    if any(kw in text_lower for kw in communication_keywords):
        if any(s in ["коммуникация", "переговоры", "документация"] for s in employee_skills_lower):
            bonus += 0.15

    if any(kw in text_lower for kw in leadership_keywords):
        if any(s in ["лидерство", "teamlead", "scrum", "agile"] for s in employee_skills_lower):
            bonus += 0.15

    return bonus


def match_employees_to_tasks(tasks: List[dict], employees: List[dict]) -> MatchResult:
    assignments = []
    employee_loads: Dict[str, int] = {e["name"]: 0 for e in employees}

    for task in tasks:
        task_type = detect_task_type(task.get("text", ""), task.get("type", ""))
        best_employee = None
        best_score = -1.0

        for employee in employees:
            hard_match = calculate_skill_match(employee, task_type)
            soft_bonus = calculate_soft_skill_bonus(employee, task.get("text", ""))
            load_penalty = employee_loads[employee["name"]] * 0.1
            total_score = hard_match * 0.6 + soft_bonus * 0.2 - load_penalty * 0.2

            if total_score > best_score:
                best_score = total_score
                best_employee = employee

        if best_employee:
            employee_loads[best_employee["name"]] += 1

            hard_skills = [s for s in best_employee.get("skills", [])
                          if any(ts in s.lower() for ts in TASK_SKILL_MAP.get(task_type, []))]
            reason = f"Hard skills: {', '.join(hard_skills[:2]) if hard_skills else 'общая компетентность'}"
            if best_score > 0.7:
                reason += ", высокая совместимость"

            assignments.append(AssignmentItem(
                task=task.get("text", ""),
                employee=best_employee["name"],
                reason=reason
            ))

    if assignments:
        avg_confidence = int(sum(
            calculate_skill_match(
                next(e for e in employees if e["name"] == a.employee),
                detect_task_type(a.task, "")
            ) for a in assignments
        ) / len(assignments) * 100)
    else:
        avg_confidence = 0

    return MatchResult(
        assignments=assignments,
        confidence=min(99, max(50, avg_confidence))
    )
