import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


def utc_now():
    return datetime.utcnow()


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    specialization: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    projects_history: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    key_results: Mapped[list] = mapped_column(JSON, default=list)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_score: Mapped[int] = mapped_column(Integer, default=0)
    validation_checks: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    chat_history: Mapped[list] = mapped_column(JSON, default=list)  # [{role, content}, ...]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    decompositions: Mapped[List["GoalDecomposition"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    assignments: Mapped[List["GoalAssignment"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    tasks: Mapped[List["Task"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    versions: Mapped[List["GoalVersion"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin", order_by="GoalVersion.created_at.desc()"
    )


class GoalVersion(Base):
    __tablename__ = "goal_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    step: Mapped[str] = mapped_column(String(50), nullable=False)  # validate, decompose, match
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    goal: Mapped["Goal"] = relationship(back_populates="versions")


class GoalDecomposition(Base):
    __tablename__ = "goal_decompositions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    company_goal: Mapped[str] = mapped_column(Text, nullable=False)
    team_goals: Mapped[list] = mapped_column(JSON, default=list)  # [{"team_id": ..., "text": ...}]
    individual_goal: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    traceability_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    goal: Mapped["Goal"] = relationship(back_populates="decompositions")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    team_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(100), default="general")
    assigned_employee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    goal: Mapped["Goal"] = relationship(back_populates="tasks")


class GoalAssignment(Base):
    __tablename__ = "goal_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    decomposition_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("goal_decompositions.id", ondelete="SET NULL"), nullable=True
    )
    task_text: Mapped[str] = mapped_column(Text, nullable=False)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    goal: Mapped["Goal"] = relationship(back_populates="assignments")
