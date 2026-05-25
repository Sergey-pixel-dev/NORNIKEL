import uuid
from datetime import datetime
from typing import List

from sqlalchemy import String, Boolean, Integer, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


def utc_now():
    return datetime.utcnow()


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_score: Mapped[int] = mapped_column(Integer, default=0)
    validation_checks: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)

    decompositions: Mapped[List["GoalDecomposition"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )
    assignments: Mapped[List["GoalAssignment"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan", lazy="selectin"
    )


class GoalDecomposition(Base):
    __tablename__ = "goal_decompositions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"))
    company_goal: Mapped[str] = mapped_column(Text, nullable=False)
    team_goals: Mapped[list] = mapped_column(JSON, default=list)
    individual_goal: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    traceability_score: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)

    goal: Mapped["Goal"] = relationship(back_populates="decompositions")


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
