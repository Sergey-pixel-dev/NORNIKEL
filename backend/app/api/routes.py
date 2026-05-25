from fastapi import APIRouter
from app.models import (
    GoalInput, ValidationResult,
    DecomposeInput, DecomposeResult,
    MatchInput, MatchResult
)
from app.agent.validator import validate_goal
from app.agent.decomposer import decompose_goal
from app.agent.matcher import match_employees_to_tasks

router = APIRouter(prefix="/api")


@router.post("/validate", response_model=ValidationResult)
async def api_validate_goal(input_data: GoalInput):
    """Проверяет цель на соответствие SMART-критериям."""
    return validate_goal(input_data.goal, input_data.key_results)


@router.post("/decompose", response_model=DecomposeResult)
async def api_decompose(input_data: DecomposeInput):
    """Декомпозирует цель на уровни: компания → команды → сотрудники."""
    return decompose_goal(input_data.goal)


@router.post("/match", response_model=MatchResult)
async def api_match(input_data: MatchInput):
    """Подбирает исполнителей для задач на основе скиллов."""
    return match_employees_to_tasks(input_data.tasks, input_data.employees)
