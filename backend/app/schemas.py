from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class ValidationCheckSchema(BaseModel):
    name: str
    passed: bool
    message: str


class GoalCreate(BaseModel):
    title: Optional[str] = None
    description: str
    key_results: List[str] = []


class GoalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    is_valid: bool
    validation_score: int
    validation_checks: list
    suggestions: list
    created_at: datetime
    updated_at: datetime


class GoalList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    is_valid: bool
    validation_score: int
    created_at: datetime


class GoalUpdateValidation(BaseModel):
    is_valid: bool
    validation_score: int
    validation_checks: list
    suggestions: list
    title: Optional[str] = None


class GoalDecompositionCreate(BaseModel):
    company_goal: str
    team_goals: List[str]
    individual_goal: str
    reasoning: str
    traceability_score: int


class GoalDecompositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_goal: str
    team_goals: List[str]
    individual_goal: str
    reasoning: str
    traceability_score: int
    created_at: datetime


class GoalAssignmentCreate(BaseModel):
    task_text: str
    employee_name: str
    reason: str


class GoalAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_text: str
    employee_name: str
    reason: str
    created_at: datetime


class GoalDetailRead(GoalRead):
    decompositions: List[GoalDecompositionRead] = []
    assignments: List[GoalAssignmentRead] = []


class AssignmentItem(BaseModel):
    task: str
    employee: str
    reason: str


class MatchInput(BaseModel):
    tasks: List[dict]
    employees: List[dict]


class MatchResult(BaseModel):
    assignments: List[AssignmentItem]
    confidence: int
