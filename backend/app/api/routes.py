from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.crud.goals import (
    create_goal, get_goals, get_goal, update_goal_validation,
    create_decomposition, create_assignments
)
from app.schemas import (
    GoalCreate, GoalRead, GoalList, GoalDetailRead,
    GoalUpdateValidation, GoalDecompositionCreate, GoalAssignmentCreate,
    MatchResult
)
from app.agent.validator import validate_goal
from app.agent.decomposer import decompose_goal
from app.agent.matcher import match_employees_to_tasks
from app.agent.title_generator import generate_title

router = APIRouter(prefix="/api")


@router.post("/validate", response_model=dict)
async def api_validate_goal(data: GoalCreate, db: AsyncSession = Depends(get_db)):
    """Проверяет цель на SMART, генерирует заголовок, сохраняет в БД."""
    # Генерируем заголовок если не указан
    title = data.title or generate_title(data.description)

    # Валидация
    validation = validate_goal(data.description, data.key_results)

    # Создаем цель в БД
    goal = await create_goal(db, GoalCreate(title=title, description=data.description, key_results=data.key_results))

    # Обновляем результатами валидации
    await update_goal_validation(
        db, goal.id,
        GoalUpdateValidation(
            is_valid=validation.is_valid,
            validation_score=validation.score,
            validation_checks=[c.model_dump() for c in validation.checks],
            suggestions=validation.suggestions,
            title=title,
        )
    )

    return {
        "goal_id": str(goal.id),
        "title": title,
        "validation": validation.model_dump(),
    }


@router.get("/goals", response_model=List[GoalList])
async def api_list_goals(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Список всех целей."""
    goals = await get_goals(db, skip=skip, limit=limit)
    return goals


@router.get("/goals/{goal_id}", response_model=GoalDetailRead)
async def api_get_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Одна цель с декомпозицией и назначениями."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    return goal


@router.post("/goals/{goal_id}/decompose", response_model=dict)
async def api_decompose_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Декомпозирует цель и сохраняет результат."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    result = decompose_goal(goal.description)

    decomposition = await create_decomposition(
        db, goal_id,
        GoalDecompositionCreate(
            company_goal=result.company,
            team_goals=result.teams,
            individual_goal=result.individual,
            reasoning=result.reasoning,
            traceability_score=result.traceability_score,
        )
    )

    return {
        "decomposition_id": str(decomposition.id),
        "company": result.company,
        "teams": result.teams,
        "individual": result.individual,
        "reasoning": result.reasoning,
        "traceability_score": result.traceability_score,
    }


@router.post("/goals/{goal_id}/match", response_model=MatchResult)
async def api_match_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Выполняет матчинг для задач декомпозиции цели."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    # Берем последнюю декомпозицию
    if not goal.decompositions:
        raise HTTPException(status_code=400, detail="Цель не декомпозирована")

    decomposition = goal.decompositions[-1]

    # Формируем задачи из декомпозиции
    tasks = [
        {"text": decomposition.team_goals[0] if decomposition.team_goals else "Задача команды A", "type": "Backend"},
        {"text": decomposition.team_goals[1] if len(decomposition.team_goals) > 1 else "Задача команды B", "type": "Frontend"},
        {"text": decomposition.individual_goal, "type": "ML"},
    ]

    # Демо-сотрудники (в реальности будут из БД)
    employees = [
        {"name": "Петров С.А.", "role": "Data Scientist", "skills": ["python", "ml", "data-analysis"]},
        {"name": "Иванова К.М.", "role": "Frontend-разработчик", "skills": ["react", "js", "ui-design"]},
        {"name": "Сидоров Д.В.", "role": "Team Lead", "skills": ["java", "spring", "teamlead"]},
        {"name": "Козлова А.Р.", "role": "BI-аналитик", "skills": ["sql", "bi", "reporting"]},
    ]

    result = match_employees_to_tasks(tasks, employees)

    # Сохраняем назначения
    assignments = [
        GoalAssignmentCreate(task_text=a.task, employee_name=a.employee, reason=a.reason)
        for a in result.assignments
    ]
    await create_assignments(db, goal_id, assignments)

    return result
