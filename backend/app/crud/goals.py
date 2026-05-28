from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.models import (
    Goal, GoalDecomposition, GoalAssignment, GoalVersion,
    Team, Employee, Task
)
from app.schemas import (
    GoalCreate, GoalUpdateValidation, GoalDecompositionCreate,
    GoalAssignmentCreate, GoalVersionCreate, TaskCreate, TaskUpdate
)


# --- Goals ---

async def create_goal(db: AsyncSession, goal_data: GoalCreate) -> Goal:
    goal = Goal(
        title=goal_data.title or "",
        description=goal_data.description,
        key_results=goal_data.key_results or [],
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal


async def get_goals(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Goal]:
    result = await db.execute(
        select(Goal).order_by(desc(Goal.created_at)).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_goal(db: AsyncSession, goal_id: UUID) -> Optional[Goal]:
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    return result.scalar_one_or_none()


async def update_goal(
    db: AsyncSession, goal_id: UUID, **kwargs
) -> Optional[Goal]:
    goal = await get_goal(db, goal_id)
    if not goal:
        return None
    for k, v in kwargs.items():
        if hasattr(goal, k):
            setattr(goal, k, v)
    await db.commit()
    await db.refresh(goal)
    return goal


async def append_chat_message(db: AsyncSession, goal_id: UUID, role: str, content: str) -> Optional[Goal]:
    goal = await get_goal(db, goal_id)
    if not goal:
        return None
    new_history = list(goal.chat_history or [])
    new_history.append({"role": role, "content": content})
    goal.chat_history = new_history
    await db.commit()
    await db.refresh(goal)
    return goal


async def reset_chat_history(db: AsyncSession, goal_id: UUID) -> Optional[Goal]:
    goal = await get_goal(db, goal_id)
    if not goal:
        return None
    goal.chat_history = []
    await db.commit()
    await db.refresh(goal)
    return goal


async def update_goal_validation(
    db: AsyncSession, goal_id: UUID, data: GoalUpdateValidation
) -> Optional[Goal]:
    goal = await get_goal(db, goal_id)
    if not goal:
        return None
    goal.is_valid = data.is_valid
    goal.validation_score = data.validation_score
    goal.validation_checks = data.validation_checks
    goal.suggestions = data.suggestions
    if data.title:
        goal.title = data.title
    await db.commit()
    await db.refresh(goal)
    return goal


# --- Decompositions ---

async def create_decomposition(
    db: AsyncSession, goal_id: UUID, data: GoalDecompositionCreate
) -> GoalDecomposition:
    decomposition = GoalDecomposition(
        goal_id=goal_id,
        company_goal=data.company_goal,
        team_goals=data.team_goals,
        individual_goal=data.individual_goal,
        reasoning=data.reasoning,
        traceability_score=data.traceability_score,
    )
    db.add(decomposition)
    await db.commit()
    await db.refresh(decomposition)
    return decomposition


# --- Assignments (legacy) ---

async def create_assignments(
    db: AsyncSession, goal_id: UUID, assignments: List[GoalAssignmentCreate]
) -> List[GoalAssignment]:
    created = []
    for item in assignments:
        assignment = GoalAssignment(
            goal_id=goal_id,
            task_text=item.task_text,
            employee_name=item.employee_name,
            reason=item.reason,
        )
        db.add(assignment)
        created.append(assignment)
    await db.commit()
    for a in created:
        await db.refresh(a)
    return created


async def delete_assignments_by_goal(db: AsyncSession, goal_id: UUID):
    result = await db.execute(select(GoalAssignment).where(GoalAssignment.goal_id == goal_id))
    for a in result.scalars().all():
        await db.delete(a)
    await db.commit()


# --- Teams ---

async def get_teams(db: AsyncSession) -> List[Team]:
    result = await db.execute(select(Team).order_by(Team.name))
    return result.scalars().all()


# --- Employees ---

async def get_employees(db: AsyncSession) -> List[Employee]:
    result = await db.execute(select(Employee).order_by(Employee.name))
    return result.scalars().all()


async def get_employee(db: AsyncSession, employee_id: UUID) -> Optional[Employee]:
    result = await db.execute(select(Employee).where(Employee.id == employee_id))
    return result.scalar_one_or_none()


async def get_employees_by_team(db: AsyncSession, team_id: UUID) -> List[Employee]:
    result = await db.execute(
        select(Employee).where(Employee.team_id == team_id).order_by(Employee.name)
    )
    return result.scalars().all()


# --- Tasks ---

async def create_task(db: AsyncSession, data: TaskCreate) -> Task:
    task = Task(
        goal_id=data.goal_id,
        team_id=data.team_id,
        text=data.text,
        type=data.type,
        order=data.order,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def get_tasks_by_goal(db: AsyncSession, goal_id: UUID) -> List[Task]:
    result = await db.execute(
        select(Task).where(Task.goal_id == goal_id).order_by(Task.order)
    )
    return result.scalars().all()


async def update_task(db: AsyncSession, task_id: UUID, data: TaskUpdate) -> Optional[Task]:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return None
    if data.text is not None:
        task.text = data.text
    if data.type is not None:
        task.type = data.type
    if data.assigned_employee_id is not None:
        task.assigned_employee_id = data.assigned_employee_id
    if data.order is not None:
        task.order = data.order
    await db.commit()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task_id: UUID) -> bool:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        return False
    await db.delete(task)
    await db.commit()
    return True


# --- Versions ---

async def create_version(db: AsyncSession, data: GoalVersionCreate) -> GoalVersion:
    version = GoalVersion(
        goal_id=data.goal_id,
        step=data.step,
        payload=data.payload,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)
    return version


async def get_versions_by_goal(db: AsyncSession, goal_id: UUID) -> List[GoalVersion]:
    result = await db.execute(
        select(GoalVersion).where(GoalVersion.goal_id == goal_id).order_by(desc(GoalVersion.created_at))
    )
    return result.scalars().all()
