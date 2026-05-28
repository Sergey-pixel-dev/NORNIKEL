import asyncio
from typing import List

from app.agent import ollama_client
from app.agent.ai_mock import ai_rewrite_goal as mock_rewrite, _generate_krs
from app.agent.decomposer import decompose_goal as mock_decompose
from app.agent.matcher import match_employees_to_tasks


async def rewrite_goal(text: str) -> dict:
    """Переписывает цель через LLM, fallback на mock."""
    try:
        return await asyncio.wait_for(ollama_client.rewrite_goal(text), timeout=35)
    except Exception as e:
        print(f"[AI] LLM rewrite failed ({e}), using mock")
        return mock_rewrite(text)


async def decompose_goal(goal: str, teams: List[dict]) -> dict:
    """Декомпозирует цель через LLM, fallback на mock."""
    try:
        result = await asyncio.wait_for(ollama_client.decompose_goal_llm(goal, teams), timeout=35)
        # Добавляем company goal
        from app.models import DecomposeResult
        return DecomposeResult(
            company=goal,
            teams=result["teams"],
            individual=result.get("individual", ""),
            reasoning=result.get("reasoning", ""),
            traceability_score=result.get("traceability_score", 85),
        )
    except Exception as e:
        print(f"[AI] LLM decompose failed ({e}), using mock")
        return mock_decompose(goal, teams)


async def suggest_assignments(tasks: List[dict], employees: List[dict]) -> List[dict]:
    """Предлагает назначения через LLM, fallback на mock matcher."""
    try:
        suggestions = await asyncio.wait_for(
            ollama_client.suggest_assignments_llm(tasks, employees), timeout=35
        )
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
