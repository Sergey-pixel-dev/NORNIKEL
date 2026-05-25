from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.models import Goal, GoalDecomposition, GoalAssignment
from app.schemas import GoalCreate, GoalUpdateValidation, GoalDecompositionCreate, GoalAssignmentCreate


async def create_goal(db: AsyncSession, goal_data: GoalCreate) -> Goal:
    goal = Goal(
        title=goal_data.title or "",
        description=goal_data.description,
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
