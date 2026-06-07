from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import User, Employee, Team
from app.schemas import UserLogin, TokenResponse, UserRead
from app.services.auth import verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth")


@router.post("/login", response_model=TokenResponse)
async def api_login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserRead.model_validate(user),
    )


@router.get("/me")
async def api_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Employee).where(Employee.user_id == user.id)
    )
    employee = result.scalar_one_or_none()

    team_id: Optional[UUID] = None
    team_name: Optional[str] = None
    if employee and employee.team_id:
        team_result = await db.execute(select(Team).where(Team.id == employee.team_id))
        team = team_result.scalar_one_or_none()
        if team:
            team_id = team.id
            team_name = team.name

    return {
        "user": UserRead.model_validate(user),
        "employee": {
            "id": str(employee.id) if employee else None,
            "name": employee.name if employee else None,
            "role": employee.role if employee else None,
            "team_id": str(employee.team_id) if employee and employee.team_id else None,
            "skills": employee.skills if employee else [],
            "projects_history": employee.projects_history if employee else [],
        } if employee else None,
        "team_id": str(team_id) if team_id else None,
        "team_name": team_name,
    }
