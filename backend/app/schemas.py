from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
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
    key_results: List[str]
    is_valid: bool
    validation_score: int
    validation_checks: list
    suggestions: list
    chat_history: list
    created_at: datetime
    updated_at: datetime


class GoalList(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    is_valid: bool
    validation_score: int
    chat_history: list
    created_at: datetime


class GoalUpdateValidation(BaseModel):
    is_valid: bool
    validation_score: int
    validation_checks: list
    suggestions: list
    title: Optional[str] = None


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    specialization: str
    description: str


class EmployeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: str
    skills: List[str]
    projects_history: List[str]


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    text: str
    type: str
    assigned_employee_id: Optional[UUID]
    order: int
    created_at: datetime


class TaskCreate(BaseModel):
    goal_id: UUID
    text: str
    type: str = "general"
    order: int = 0


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    type: Optional[str] = None
    assigned_employee_id: Optional[UUID] = None
    order: Optional[int] = None


class GoalVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    step: str
    payload: Dict[str, Any]
    created_at: datetime


class GoalVersionCreate(BaseModel):
    goal_id: UUID
    step: str
    payload: Dict[str, Any]


class GoalDecompositionCreate(BaseModel):
    company_goal: str
    team_goals: List[dict]
    individual_goal: str
    reasoning: str
    traceability_score: int


class GoalDecompositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_goal: str
    team_goals: List[dict]
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
    tasks: List[TaskRead] = []
    versions: List[GoalVersionRead] = []


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


class DocumentUploadResponse(BaseModel):
    extracted_text: str


class AIRewriteResponse(BaseModel):
    rewritten_goal: str
    key_results: List[str]


class AssignTasksPayload(BaseModel):
    assignments: List[dict]  # [{"task_id": ..., "employee_id": ...}]
