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
    team_id: Optional[UUID]
    name: str
    role: str
    skills: List[str]
    projects_history: List[str]


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: UUID
    team_id: Optional[UUID]
    text: str
    type: str
    assigned_employee_id: Optional[UUID]
    order: int
    created_at: datetime


class TaskCreate(BaseModel):
    goal_id: UUID
    team_id: Optional[UUID] = None
    text: str
    type: str = "general"
    order: int = 0


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    team_id: Optional[UUID] = None
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


# --- Auth / Users ---

class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    role: str
    name: str
    is_active: bool
    created_at: datetime


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserRead


# --- Employees CRUD ---

class EmployeeCreate(BaseModel):
    name: str
    role: str = ""
    skills: List[str] = []
    projects_history: List[str] = []
    team_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    skills: Optional[List[str]] = None
    projects_history: Optional[List[str]] = None
    team_id: Optional[UUID] = None
    user_id: Optional[UUID] = None


# --- Reports ---

class ReportCreate(BaseModel):
    task_id: UUID
    content: str


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    author_id: UUID
    author_name: Optional[str] = None
    content: str
    status: str
    ai_score: Optional[int]
    ai_feedback: str
    reviewed_by: Optional[UUID]
    reviewed_at: Optional[datetime]
    review_comment: str
    attachment_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class ReportUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None
    ai_score: Optional[int] = None
    ai_feedback: Optional[str] = None
    reviewed_by: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    review_comment: Optional[str] = None
    attachment_url: Optional[str] = None


# --- Task updates for auth / manager fields ---

class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_id: Optional[UUID]
    team_id: Optional[UUID]
    text: str
    type: str
    assigned_employee_id: Optional[UUID]
    creator_id: Optional[UUID]
    manager_task_type: Optional[str]
    order: int
    created_at: datetime


class TaskCreate(BaseModel):
    goal_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    text: str
    type: str = "general"
    assigned_employee_id: Optional[UUID] = None
    creator_id: Optional[UUID] = None
    manager_task_type: Optional[str] = None
    order: int = 0


class TaskUpdate(BaseModel):
    text: Optional[str] = None
    team_id: Optional[UUID] = None
    type: Optional[str] = None
    assigned_employee_id: Optional[UUID] = None
    creator_id: Optional[UUID] = None
    manager_task_type: Optional[str] = None
    order: Optional[int] = None
