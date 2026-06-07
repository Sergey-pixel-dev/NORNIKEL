import asyncio
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import ollama_client
from app.agent.ai_mock import ai_rewrite_goal as mock_rewrite, mock_check_report
from app.agent.decomposer import decompose_goal as mock_decompose
from app.agent.matcher import match_employees_to_tasks
from app.crud.goals import append_chat_message, get_goal


SYSTEM_PROMPT = (
    "Ты — ИИ-ассистент OKR для компании Норникель. "
    "Ты помогаешь директорам и руководителям: проверять цели на SMART, "
    "декомпозировать их на команды с учётом специализации, и распределять задачи по сотрудникам. "
    "Ты всегда отвечаешь строго в запрошенном формате, без лишних слов."
)


def _history_from_goal(goal) -> List[dict]:
    hist = list(goal.chat_history or [])
    if not hist or hist[0].get("role") != "system":
        hist = [{"role": "system", "content": SYSTEM_PROMPT}] + hist
    return hist


async def rewrite_goal(db: AsyncSession, goal_id: UUID, text: str) -> dict:
    goal = await get_goal(db, goal_id)
    if not goal:
        raise ValueError("Цель не найдена")

    history = _history_from_goal(goal)
    try:
        result = await asyncio.wait_for(ollama_client.rewrite_goal(history, text), timeout=35)
        # Сохраняем в историю
        await append_chat_message(db, goal_id, "user", f"Перепиши цель: {text}")
        await append_chat_message(db, goal_id, "assistant", f"ЦЕЛЬ: {result['rewritten_goal']}\n" + "\n".join([f"KR{i+1}: {kr}" for i, kr in enumerate(result['key_results'])]))
        return result
    except Exception as e:
        print(f"[AI] LLM rewrite failed ({e}), using mock")
        return mock_rewrite(text)


async def decompose_goal(db: AsyncSession, goal_id: UUID, goal_text: str, teams: List[dict]):
    goal = await get_goal(db, goal_id)
    if not goal:
        raise ValueError("Цель не найдена")

    history = _history_from_goal(goal)
    try:
        result = await asyncio.wait_for(ollama_client.decompose_goal_llm(history, goal_text, teams), timeout=35)
        # Сохраняем в историю
        teams_text = "\n".join([f"{t['team_name']}: {t['text']}" for t in result["teams"]])
        await append_chat_message(db, goal_id, "user", f"Декомпозируй цель на команды: {goal_text}")
        await append_chat_message(db, goal_id, "assistant", f"Разбивка:\n{teams_text}\nОбоснование: {result['reasoning']}")
        from app.models import DecomposeResult
        return DecomposeResult(
            company=goal_text,
            teams=result["teams"],
            individual=result.get("individual", ""),
            reasoning=result.get("reasoning", ""),
            traceability_score=result.get("traceability_score", 85),
        )
    except Exception as e:
        print(f"[AI] LLM decompose failed ({e}), using mock")
        return mock_decompose(goal_text, teams)


async def suggest_assignments(db: AsyncSession, goal_id: UUID, tasks: List[dict], employees: List[dict]) -> List[dict]:
    goal = await get_goal(db, goal_id)
    if not goal:
        raise ValueError("Цель не найдена")

    history = _history_from_goal(goal)
    try:
        suggestions = await asyncio.wait_for(
            ollama_client.suggest_assignments_llm(history, tasks, employees), timeout=35
        )
        # Сохраняем в историю
        assign_text = "\n".join([f"{s['task_text'][:40]}… → {s['employee_name']}" for s in suggestions])
        await append_chat_message(db, goal_id, "user", "Распредели задачи по сотрудникам")
        await append_chat_message(db, goal_id, "assistant", f"Распределение:\n{assign_text}")
        return suggestions
    except Exception as e:
        print(f"[AI] LLM suggest assignments failed ({e}), using mock matcher")
        result = match_employees_to_tasks(tasks, employees)
        suggestions = []
        for i, a in enumerate(result.assignments):
            emp = next((e for e in employees if e["name"] == a.employee), None)
            task = tasks[i] if i < len(tasks) else {"id": None, "text": a.task}
            suggestions.append({
                "task_id": task.get("id"),
                "task_text": a.task,
                "employee_id": emp.get("id") if emp else None,
                "employee_name": a.employee,
                "reason": a.reason,
            })
        return suggestions


async def check_report_quality(report_text: str, task_text: str) -> dict:
    try:
        result = await asyncio.wait_for(
            ollama_client.check_report_llm(report_text, task_text), timeout=35
        )
        return result
    except Exception as e:
        print(f"[AI] LLM report check failed ({e}), using mock")
        return mock_check_report(report_text, task_text)


class BreakdownResult:
    def __init__(self, subtasks: List[str], reasoning: str):
        self.subtasks = subtasks
        self.reasoning = reasoning


async def breakdown_team_task(
    db: AsyncSession,
    goal_id: UUID,
    team_name: str,
    team_task: str,
    specialization: str,
    goal_desc: str,
    employees: List[dict],
) -> BreakdownResult:
    goal = await get_goal(db, goal_id)
    if not goal:
        raise ValueError("Цель не найдена")

    history = _history_from_goal(goal)
    try:
        result = await asyncio.wait_for(
            ollama_client.breakdown_team_task_llm(
                history, team_name, team_task, specialization, goal_desc, employees
            ),
            timeout=35,
        )
        await append_chat_message(
            db, goal_id, "user",
            f"Разбей задачу команды '{team_name}' на подзадачи: {team_task}"
        )
        await append_chat_message(
            db, goal_id, "assistant",
            f"Подзадачи:\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(result['subtasks'])])
            + f"\nОбоснование: {result['reasoning']}"
        )
        return BreakdownResult(subtasks=result["subtasks"], reasoning=result["reasoning"])
    except Exception as e:
        print(f"[AI] LLM breakdown failed ({e}), using mock")
        # Fallback mock
        fallback = [
            f"Анализ требований для задачи '{team_task}'",
            f"Разработка MVP с использованием {specialization}",
            f"Тестирование и документирование результатов",
        ]
        return BreakdownResult(subtasks=fallback, reasoning="Mock fallback breakdown")
