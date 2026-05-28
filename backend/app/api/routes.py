from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.crud.goals import (
    create_goal, get_goals, get_goal, update_goal_validation, update_goal,
    create_decomposition, create_assignments, delete_assignments_by_goal,
    get_teams, get_employees, get_employee,
    create_task, get_tasks_by_goal, update_task, delete_task,
    create_version, get_versions_by_goal
)
from app.schemas import (
    GoalCreate, GoalRead, GoalList, GoalDetailRead,
    GoalUpdateValidation, GoalDecompositionCreate, GoalAssignmentCreate,
    MatchResult, DocumentUploadResponse, AIRewriteResponse,
    TeamRead, EmployeeRead, TaskRead, TaskCreate, TaskUpdate,
    GoalVersionCreate, GoalVersionRead, AssignTasksPayload
)
from app.agent.validator import validate_goal
from app.agent.decomposer import decompose_goal
from app.agent.matcher import match_employees_to_tasks
from app.agent.title_generator import generate_title
from app.agent.document_parser import extract_text
from app.agent.ai_service import rewrite_goal, decompose_goal, suggest_assignments

router = APIRouter(prefix="/api")


# --- Health / Info ---

@router.post("/validate", response_model=dict)
async def api_validate_goal(data: GoalCreate, db: AsyncSession = Depends(get_db)):
    """Проверяет цель на SMART, генерирует заголовок, сохраняет в БД."""
    title = data.title or generate_title(data.description)
    validation = validate_goal(data.description, data.key_results)

    goal = await create_goal(db, GoalCreate(
        title=title,
        description=data.description,
        key_results=data.key_results
    ))

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

    # Создаём начальную версию
    await create_version(db, GoalVersionCreate(
        goal_id=goal.id,
        step="validate",
        payload={"description": data.description, "key_results": data.key_results}
    ))

    return {
        "goal_id": str(goal.id),
        "title": title,
        "validation": validation.model_dump(),
    }


@router.post("/upload-document", response_model=DocumentUploadResponse)
async def api_upload_document(file: UploadFile = File(...)):
    """Загружает PDF/DOCX и возвращает извлечённый текст."""
    contents = await file.read()
    try:
        text = extract_text(file.filename, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DocumentUploadResponse(extracted_text=text)


@router.post("/ai-rewrite", response_model=AIRewriteResponse)
async def api_ai_rewrite(data: dict):
    """Переписывает цель и генерирует KR при помощи LLM (fallback на mock)."""
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="Передайте 'text'")
    result = await rewrite_goal(text)
    return AIRewriteResponse(rewritten_goal=result["rewritten_goal"], key_results=result["key_results"])


# --- Goals ---

@router.get("/goals", response_model=List[GoalList])
async def api_list_goals(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    goals = await get_goals(db, skip=skip, limit=limit)
    return goals


@router.get("/goals/{goal_id}", response_model=GoalDetailRead)
async def api_get_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    return goal


# --- Decomposition ---

@router.post("/goals/{goal_id}/decompose", response_model=dict)
async def api_decompose_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Декомпозирует цель с учётом команд из БД."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    teams = await get_teams(db)
    result = await decompose_goal(goal.description, teams=[{"name": t.name, "specialization": t.specialization} for t in teams])

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

    # Сохраняем версию
    await create_version(db, GoalVersionCreate(
        goal_id=goal_id,
        step="decompose",
        payload={"company": result.company, "teams": result.teams, "individual": result.individual}
    ))

    return {
        "decomposition_id": str(decomposition.id),
        "company": result.company,
        "teams": result.teams,
        "individual": result.individual,
        "reasoning": result.reasoning,
        "traceability_score": result.traceability_score,
    }


# --- Tasks ---

@router.post("/goals/{goal_id}/generate-tasks", response_model=List[TaskRead])
async def api_generate_tasks(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Mock-ИИ генерирует задачи на основе последней декомпозиции."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    if not goal.decompositions:
        raise HTTPException(status_code=400, detail="Цель не декомпозирована")

    decomposition = goal.decompositions[-1]

    # Генерируем задачи из team_goals + individual
    tasks_data = []
    order = 0
    for tg in decomposition.team_goals:
        if isinstance(tg, dict):
            text = tg.get("text", "")
        else:
            text = str(tg)
        tasks_data.append({"text": text, "type": "team", "order": order})
        order += 1

    tasks_data.append({"text": decomposition.individual_goal, "type": "individual", "order": order})

    # Удаляем старые задачи цели
    old_tasks = await get_tasks_by_goal(db, goal_id)
    for t in old_tasks:
        await delete_task(db, t.id)

    created = []
    for td in tasks_data:
        task = await create_task(db, TaskCreate(goal_id=goal_id, **td))
        created.append(task)

    # Версия
    await create_version(db, GoalVersionCreate(
        goal_id=goal_id,
        step="generate_tasks",
        payload={"tasks": [{"text": t.text, "type": t.type} for t in created]}
    ))

    return created


@router.get("/goals/{goal_id}/tasks", response_model=List[TaskRead])
async def api_list_tasks(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_tasks_by_goal(db, goal_id)


@router.post("/tasks", response_model=TaskRead)
async def api_create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    return await create_task(db, data)


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def api_update_task(task_id: UUID, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    task = await update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return task


@router.delete("/tasks/{task_id}")
async def api_delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    ok = await delete_task(db, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    return {"ok": True}


# --- Assignments ---

@router.post("/goals/{goal_id}/assign")
async def api_assign_tasks(goal_id: UUID, payload: AssignTasksPayload, db: AsyncSession = Depends(get_db)):
    """Сохраняет ручные назначения сотрудников на задачи."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    # Удаляем старые legacy-ассайнменты
    await delete_assignments_by_goal(db, goal_id)

    # Обновляем задачи
    for item in payload.assignments:
        task_id = item.get("task_id")
        employee_id = item.get("employee_id")
        if task_id:
            await update_task(db, UUID(task_id), TaskUpdate(assigned_employee_id=employee_id))

    # Сохраняем версию
    await create_version(db, GoalVersionCreate(
        goal_id=goal_id,
        step="assign",
        payload={"assignments": [a.model_dump() if hasattr(a, "model_dump") else a for a in payload.assignments]}
    ))

    return {"ok": True}


# --- Versions / Rollback ---

@router.get("/goals/{goal_id}/versions", response_model=List[GoalVersionRead])
async def api_list_versions(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    return await get_versions_by_goal(db, goal_id)


@router.post("/goals/{goal_id}/rollback")
async def api_rollback(goal_id: UUID, data: dict, db: AsyncSession = Depends(get_db)):
    """Откатывает цель к выбранной версии (восстанавливает description/KR)."""
    version_id = data.get("version_id")
    if not version_id:
        raise HTTPException(status_code=400, detail="Передайте version_id")

    versions = await get_versions_by_goal(db, goal_id)
    target = next((v for v in versions if str(v.id) == version_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Версия не найдена")

    payload = target.payload or {}
    updates = {}
    if "description" in payload:
        updates["description"] = payload["description"]
    if "key_results" in payload:
        updates["key_results"] = payload["key_results"]

    if updates:
        await update_goal(db, goal_id, **updates)

    return {"ok": True, "restored_version_id": version_id, "step": target.step}


# --- Teams & Employees ---

@router.get("/teams", response_model=List[TeamRead])
async def api_list_teams(db: AsyncSession = Depends(get_db)):
    return await get_teams(db)


@router.get("/employees", response_model=List[EmployeeRead])
async def api_list_employees(db: AsyncSession = Depends(get_db)):
    return await get_employees(db)


# --- AI Match (suggest & apply) ---

@router.post("/goals/{goal_id}/suggest-assignments")
async def api_suggest_assignments(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """ИИ предлагает распределение задач по сотрудникам (без сохранения)."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    tasks_db = await get_tasks_by_goal(db, goal_id)
    if not tasks_db:
        raise HTTPException(status_code=400, detail="У цели нет задач. Сначала сгенерируйте задачи.")

    employees_db = await get_employees(db)
    employees = [
        {"id": str(e.id), "name": e.name, "role": e.role, "skills": [s.lower() for s in e.skills]}
        for e in employees_db
    ]

    tasks = [{"id": str(t.id), "text": t.text, "type": t.type} for t in tasks_db]
    suggestions = await suggest_assignments(tasks, employees)

    return {"suggestions": suggestions}


@router.post("/goals/{goal_id}/match", response_model=MatchResult)
async def api_match_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Выполняет автоматический матчинг для задач декомпозиции цели."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    if not goal.decompositions:
        raise HTTPException(status_code=400, detail="Цель не декомпозирована")

    decomposition = goal.decompositions[-1]

    tasks = [
        {"text": decomposition.team_goals[0] if decomposition.team_goals else "Задача команды A", "type": "Backend"},
        {"text": decomposition.team_goals[1] if len(decomposition.team_goals) > 1 else "Задача команды B", "type": "Frontend"},
        {"text": decomposition.individual_goal, "type": "ML"},
    ]

    employees_db = await get_employees(db)
    employees = [
        {"name": e.name, "role": e.role, "skills": [s.lower() for s in e.skills]}
        for e in employees_db
    ]

    result = match_employees_to_tasks(tasks, employees)

    assignments = [
        GoalAssignmentCreate(task_text=a.task, employee_name=a.employee, reason=a.reason)
        for a in result.assignments
    ]
    await create_assignments(db, goal_id, assignments)

    return result
