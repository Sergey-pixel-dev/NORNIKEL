from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Employee, Task, Report
from app.crud.goals import (
    create_goal, get_goal, update_goal_validation, update_goal,
    create_decomposition, create_assignments, delete_assignments_by_goal,
    get_teams, get_employee, get_employees_by_team,
    get_teams_for_user, get_employees_for_user, get_goals_for_user,
    get_tasks_for_user, create_employee, update_employee, delete_employee,
    create_task, get_tasks_by_goal, update_task, delete_task,
    create_version, get_versions_by_goal,
    append_chat_message, reset_chat_history,
    create_report, get_report, get_reports_for_user, update_report, delete_report,
)
from app.schemas import (
    GoalCreate, GoalRead, GoalList, GoalDetailRead,
    GoalUpdateValidation, GoalDecompositionCreate, GoalAssignmentCreate,
    MatchResult, DocumentUploadResponse, AIRewriteResponse,
    TeamRead, EmployeeRead, EmployeeCreate, EmployeeUpdate, TaskRead, TaskCreate, TaskUpdate,
    GoalVersionCreate, GoalVersionRead, AssignTasksPayload,
    ReportCreate, ReportRead, ReportUpdate,
)
from app.agent.validator import validate_goal
from app.agent.decomposer import decompose_goal as mock_decompose
from app.agent.matcher import match_employees_to_tasks
from app.agent.title_generator import generate_title
from app.agent.document_parser import extract_text
from app.agent.ai_service import rewrite_goal, decompose_goal, suggest_assignments, breakdown_team_task, check_report_quality
from app.agent.ai_mock import ai_rewrite_goal as mock_rewrite
from app.services.auth import get_current_user, get_current_employee, require_role

router = APIRouter(prefix="/api")


# --- Health / Info ---

@router.post("/validate", response_model=dict)
async def api_validate_goal(
    data: GoalCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Проверяет цель на SMART, генерирует заголовок, сохраняет в БД. Только director."""
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

    kr_text = "\n".join([f"- {kr}" for kr in (data.key_results or [])])
    await append_chat_message(
        db, goal.id, "user",
        f"Валидируй цель:\n{data.description}\n\nKey Results:\n{kr_text}"
    )
    assistant_text = (
        f"Оценка: {validation.score}/100. Валидна: {validation.is_valid}.\n"
        + "\n".join([f"{'[+] ' if c.passed else '[-] '}{c.name}: {c.message}" for c in validation.checks])
    )
    await append_chat_message(db, goal.id, "assistant", assistant_text)

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
async def api_upload_document(
    file: UploadFile = File(...),
    user: User = Depends(require_role("director")),
):
    """Загружает PDF/DOCX и возвращает извлечённый текст. Только director."""
    contents = await file.read()
    try:
        text = extract_text(file.filename, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DocumentUploadResponse(extracted_text=text)


@router.post("/ai-rewrite", response_model=AIRewriteResponse)
async def api_ai_rewrite(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Переписывает цель и генерирует KR при помощи LLM. Только director."""
    text = data.get("text", "")
    goal_id = data.get("goal_id")
    if not text:
        raise HTTPException(status_code=400, detail="Передайте 'text'")

    if goal_id:
        try:
            result = await rewrite_goal(db, UUID(goal_id), text)
            return AIRewriteResponse(rewritten_goal=result["rewritten_goal"], key_results=result["key_results"])
        except Exception as e:
            print(f"[AI] rewrite with context failed ({e}), using stateless mock")

    result = mock_rewrite(text)
    return AIRewriteResponse(rewritten_goal=result.rewritten_goal, key_results=result.key_results)


# --- Goals ---

@router.get("/goals", response_model=List[GoalList])
async def api_list_goals(
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    goals = await get_goals_for_user(db, user, employee, skip=skip, limit=limit)
    return goals


@router.get("/goals/{goal_id}", response_model=GoalDetailRead)
async def api_get_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    # employee может видеть только свои goals
    if user.role == "employee" and employee:
        task_ids = [t.id for t in goal.tasks if t.assigned_employee_id == employee.id]
        if not task_ids and goal.tasks:
            raise HTTPException(status_code=403, detail="Нет доступа к этой цели")

    # dept_head может видеть только goals своей команды
    if user.role == "dept_head" and employee and employee.team_id:
        team_task_ids = [t.id for t in goal.tasks if t.team_id == employee.team_id]
        if not team_task_ids and goal.tasks:
            raise HTTPException(status_code=403, detail="Нет доступа к этой цели")

    return goal


# --- Decomposition ---

@router.post("/goals/{goal_id}/decompose", response_model=dict)
async def api_decompose_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Декомпозирует цель на команды. Только director."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    teams = await get_teams(db)
    result = await decompose_goal(
        db, goal_id, goal.description,
        teams=[{"name": t.name, "specialization": t.specialization} for t in teams]
    )

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
async def api_generate_tasks(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Генерирует team/individual задачи из декомпозиции. Только director."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    if not goal.decompositions:
        raise HTTPException(status_code=400, detail="Цель не декомпозирована")

    decomposition = goal.decompositions[-1]

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

    old_tasks = await get_tasks_by_goal(db, goal_id)
    for t in old_tasks:
        await delete_task(db, t.id)

    created = []
    for td in tasks_data:
        task = await create_task(db, TaskCreate(goal_id=goal_id, **td))
        created.append(task)

    await create_version(db, GoalVersionCreate(
        goal_id=goal_id,
        step="generate_tasks",
        payload={"tasks": [{"text": t.text, "type": t.type} for t in created]}
    ))

    return created


@router.get("/goals/{goal_id}/tasks", response_model=List[TaskRead])
async def api_list_tasks(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    tasks = await get_tasks_by_goal(db, goal_id)
    if user.role == "director":
        tasks = [t for t in tasks if t.type in ("team", "individual")]
    elif user.role == "dept_head" and employee and employee.team_id:
        tasks = [t for t in tasks if t.team_id == employee.team_id]
    elif user.role == "employee" and employee:
        tasks = [t for t in tasks if t.assigned_employee_id == employee.id]
    return tasks


@router.get("/tasks", response_model=List[TaskRead])
async def api_list_all_tasks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    return await get_tasks_for_user(db, user, employee)


@router.post("/tasks", response_model=TaskRead)
async def api_create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    if not employee:
        raise HTTPException(status_code=400, detail="Сотрудник не связан с пользователем")

    # Employee не может создавать задачи
    if user.role == "employee":
        raise HTTPException(status_code=403, detail="Нет доступа")

    # Director может создавать только team/individual задачи
    if user.role == "director" and data.type not in ("team", "individual"):
        raise HTTPException(status_code=403, detail="Director может создавать только team/individual задачи")

    # Dept_head может создавать только для своей команды
    if user.role == "dept_head":
        if data.team_id and data.team_id != employee.team_id:
            raise HTTPException(status_code=403, detail="Можно создавать задачи только для своей команды")
        if data.goal_id is None and data.type not in ("subtask", "general", "technical", "management"):
            raise HTTPException(status_code=403, detail="Недопустимый тип задачи")

    if data.creator_id is None:
        data.creator_id = employee.id

    return await create_task(db, data)


@router.put("/tasks/{task_id}", response_model=TaskRead)
async def api_update_task(
    task_id: UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    task = await update_task(db, task_id, data)
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if user.role == "director" and task.type not in ("team", "individual"):
        raise HTTPException(status_code=403, detail="Нет доступа")

    if user.role == "dept_head" and employee:
        if task.team_id != employee.team_id:
            raise HTTPException(status_code=403, detail="Можно редактировать только задачи своей команды")

    if user.role == "employee" and employee and task.assigned_employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    return task


@router.delete("/tasks/{task_id}")
async def api_delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    task = await db.execute(select(Task).where(Task.id == task_id))
    task = task.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    if user.role == "director" and task.type not in ("team", "individual"):
        raise HTTPException(status_code=403, detail="Нет доступа")

    if user.role == "dept_head" and employee:
        if task.team_id != employee.team_id:
            raise HTTPException(status_code=403, detail="Можно удалять только задачи своей команды")

    if user.role == "employee":
        raise HTTPException(status_code=403, detail="Нет доступа")

    ok = await delete_task(db, task_id)
    return {"ok": ok}


# --- Assignments ---

@router.post("/goals/{goal_id}/suggest-assignments")
async def api_suggest_assignments(
    goal_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    """ИИ предлагает распределение задач по сотрудникам команды. Только dept_head."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    team_id_str = data.get("team_id")
    if not team_id_str:
        raise HTTPException(status_code=400, detail="Передайте team_id")

    team_uuid = UUID(team_id_str)
    if current_emp and current_emp.team_id and team_uuid != current_emp.team_id:
        raise HTTPException(status_code=403, detail="Можно распределять только в своей команде")

    tasks_db = await get_tasks_by_goal(db, goal_id)
    if not tasks_db:
        raise HTTPException(status_code=400, detail="У цели нет задач.")

    tasks_db = [t for t in tasks_db if t.team_id == team_uuid]
    employees_db = await get_employees_by_team(db, team_uuid)

    if not tasks_db:
        raise HTTPException(status_code=400, detail="У команды нет задач для распределения.")

    employees = [
        {"id": str(e.id), "name": e.name, "role": e.role, "skills": [s.lower() for s in e.skills]}
        for e in employees_db
    ]
    tasks = [{"id": str(t.id), "text": t.text, "type": t.type} for t in tasks_db]
    suggestions = await suggest_assignments(db, goal_id, tasks, employees)

    return {"suggestions": suggestions}


@router.post("/goals/{goal_id}/assign")
async def api_assign_tasks(
    goal_id: UUID,
    payload: AssignTasksPayload,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    """Сохраняет ручные назначения сотрудников на задачи. Только dept_head."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    await delete_assignments_by_goal(db, goal_id)

    for item in payload.assignments:
        task_id = item.get("task_id")
        employee_id = item.get("employee_id")
        if task_id:
            # Проверяем, что задача принадлежит команде dept_head
            t = await db.execute(select(Task).where(Task.id == UUID(task_id)))
            t = t.scalar_one_or_none()
            if t and current_emp and current_emp.team_id and t.team_id != current_emp.team_id:
                raise HTTPException(status_code=403, detail="Нельзя назначать на задачи другой команды")
            await update_task(db, UUID(task_id), TaskUpdate(assigned_employee_id=employee_id))

    await create_version(db, GoalVersionCreate(
        goal_id=goal_id,
        step="assign",
        payload={"assignments": [a.model_dump() if hasattr(a, "model_dump") else a for a in payload.assignments]}
    ))

    return {"ok": True}


# --- Versions / Rollback ---

@router.get("/goals/{goal_id}/versions", response_model=List[GoalVersionRead])
async def api_list_versions(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    return await get_versions_by_goal(db, goal_id)


@router.post("/goals/{goal_id}/rollback")
async def api_rollback(
    goal_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Откатывает цель к выбранной версии. Только director."""
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


@router.post("/goals/{goal_id}/reset-chat")
async def api_reset_chat(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Очищает историю чата для цели. Только director."""
    goal = await reset_chat_history(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")
    return {"ok": True}


# --- Teams & Employees ---

@router.get("/teams", response_model=List[TeamRead])
async def api_list_teams(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    return await get_teams_for_user(db, user, employee)


@router.get("/employees", response_model=List[EmployeeRead])
async def api_list_employees(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    return await get_employees_for_user(db, user, employee)


@router.post("/employees", response_model=EmployeeRead)
async def api_create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head", "director")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    if user.role == "dept_head" and current_emp and current_emp.team_id:
        if data.team_id != current_emp.team_id:
            raise HTTPException(status_code=403, detail="Можно добавлять только в свою команду")
    return await create_employee(db, data)


@router.put("/employees/{employee_id}", response_model=EmployeeRead)
async def api_update_employee(
    employee_id: UUID,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head", "director")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    emp = await get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if user.role == "dept_head" and current_emp and current_emp.team_id:
        if emp.team_id != current_emp.team_id:
            raise HTTPException(status_code=403, detail="Можно редактировать только свою команду")
    updated = await update_employee(db, employee_id, data)
    return updated


@router.delete("/employees/{employee_id}")
async def api_delete_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head", "director")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    emp = await get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    if user.role == "dept_head" and current_emp and current_emp.team_id:
        if emp.team_id != current_emp.team_id:
            raise HTTPException(status_code=403, detail="Можно удалять только из своей команды")
    ok = await delete_employee(db, employee_id)
    return {"ok": ok}


@router.get("/teams/{team_id}/employees", response_model=List[EmployeeRead])
async def api_list_team_employees(
    team_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    if user.role == "employee" and employee and employee.team_id != team_id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    if user.role == "dept_head" and employee and employee.team_id != team_id:
        raise HTTPException(status_code=403, detail="Можно просматривать только свою команду")
    return await get_employees_by_team(db, team_id)


@router.post("/goals/{goal_id}/breakdown-team")
async def api_breakdown_team(
    goal_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    """Разбивает задачу команды на подзадачи. Только dept_head, только своя команда."""
    goal = await get_goal(db, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Цель не найдена")

    team_id_str = data.get("team_id")
    team_name = data.get("team_name", "")
    team_task = data.get("team_task", "")
    specialization = data.get("specialization", "")
    if not team_id_str or not team_task:
        raise HTTPException(status_code=400, detail="Передайте team_id и team_task")

    team_uuid = UUID(team_id_str)
    if current_emp and current_emp.team_id and team_uuid != current_emp.team_id:
        raise HTTPException(status_code=403, detail="Можно разбивать только задачи своей команды")

    team_employees = await get_employees_by_team(db, team_uuid)
    employees_info = [
        {"name": e.name, "role": e.role, "skills": e.skills}
        for e in team_employees
    ]

    result = await breakdown_team_task(
        db, goal_id, team_name, team_task, specialization, goal.description, employees_info
    )

    old_tasks = await get_tasks_by_goal(db, goal_id)
    for t in old_tasks:
        if t.type == "subtask" and t.team_id == team_uuid:
            await delete_task(db, t.id)

    created = []
    for i, sub in enumerate(result.subtasks):
        task = await create_task(db, TaskCreate(
            goal_id=goal_id,
            team_id=team_uuid,
            text=sub,
            type="subtask",
            order=i,
        ))
        created.append(task)

    await create_version(db, GoalVersionCreate(
        goal_id=goal_id,
        step="breakdown_team",
        payload={"team_id": str(team_uuid), "team_name": team_name, "subtasks": result.subtasks}
    ))

    return {
        "team_id": str(team_uuid),
        "team_name": team_name,
        "subtasks": result.subtasks,
        "reasoning": result.reasoning,
        "task_ids": [str(t.id) for t in created],
    }


# --- Reports ---

@router.post("/reports", response_model=ReportRead)
async def api_create_report(
    data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    if not employee:
        raise HTTPException(status_code=400, detail="Сотрудник не связан с пользователем")

    task = await db.execute(select(Task).where(Task.id == data.task_id))
    task = task.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # employee может писать отчет только по своей задаче
    if user.role == "employee" and task.assigned_employee_id != employee.id:
        raise HTTPException(status_code=403, detail="Задача не назначена вам")

    # dept_head может писать отчет только по задаче своей команды
    if user.role == "dept_head" and task.team_id != employee.team_id:
        raise HTTPException(status_code=403, detail="Задача не из вашей команды")

    report = await create_report(db, data, employee.id)
    return report


@router.get("/reports", response_model=List[ReportRead])
async def api_list_reports(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    reports = await get_reports_for_user(db, user, employee)
    result = []
    for r in reports:
        data = ReportRead.model_validate(r).model_dump()
        data["author_name"] = r.author.name if r.author else None
        result.append(data)
    return result


@router.post("/reports/{report_id}/ai-check")
async def api_check_report_ai(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчет не найден")
    if user.role == "employee" and employee and report.author_id != employee.id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    if user.role == "dept_head" and employee and report.author_id != employee.id:
        # dept_head может проверять AI своих сотрудников? Да, но пока ограничим автором
        pass

    task = await db.execute(select(Task).where(Task.id == report.task_id))
    task = task.scalar_one_or_none()
    result = await check_report_quality(report.content, task.text if task else "")
    await update_report(db, report_id, ReportUpdate(
        ai_score=result.get("score"),
        ai_feedback=result.get("feedback"),
    ))
    return result


@router.post("/reports/{report_id}/submit")
async def api_submit_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчет не найден")
    if user.role == "employee" and employee and report.author_id != employee.id:
        raise HTTPException(status_code=403, detail="Нет доступа")
    updated = await update_report(db, report_id, ReportUpdate(status="pending"))
    return updated


@router.post("/reports/{report_id}/review")
async def api_review_report(
    report_id: UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("dept_head", "director")),
    current_emp: Optional[Employee] = Depends(get_current_employee),
):
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчет не найден")

    status_val = data.get("status")
    comment = data.get("comment", "")
    if status_val not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="status должен быть approved или rejected")

    # Получаем автора отчета
    author = await get_employee(db, report.author_id)
    if not author:
        raise HTTPException(status_code=404, detail="Автор отчета не найден")

    if user.role == "director":
        # Director может ревьюить только отчеты руководителей отделов
        author_user = await db.execute(select(User).where(User.id == author.user_id))
        author_user = author_user.scalar_one_or_none()
        if not author_user or author_user.role != "dept_head":
            raise HTTPException(status_code=403, detail="Можно проверять только отчеты руководителей отделов")

    elif user.role == "dept_head":
        # Dept_head может ревьюить только отчеты своей команды
        if current_emp and current_emp.team_id and author.team_id != current_emp.team_id:
            raise HTTPException(status_code=403, detail="Можно проверять только отчеты своей команды")

    from datetime import datetime
    updated = await update_report(db, report_id, ReportUpdate(
        status=status_val,
        review_comment=comment,
        reviewed_by=user.id,
        reviewed_at=datetime.utcnow(),
    ))
    return updated


@router.post("/reports/{report_id}/upload")
async def api_upload_report_attachment(
    report_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    employee: Optional[Employee] = Depends(get_current_employee),
):
    """Прикрепляет PDF к отчету."""
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Отчет не найден")

    # Только автор может прикреплять файлы
    if employee and report.author_id != employee.id:
        raise HTTPException(status_code=403, detail="Нет доступа")

    contents = await file.read()
    # Сохраняем в директорию uploads
    import os
    upload_dir = "/app/uploads/reports"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{report_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(contents)

    # Обновляем report с attachment_url
    attachment_url = f"/uploads/reports/{report_id}_{file.filename}"
    await update_report(db, report_id, ReportUpdate(attachment_url=attachment_url))

    return {"attachment_url": attachment_url}


# --- Legacy Match (mock) ---

@router.post("/goals/{goal_id}/match", response_model=MatchResult)
async def api_match_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role("director")),
):
    """Выполняет автоматический матчинг. Только director."""
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
