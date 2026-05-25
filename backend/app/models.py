from pydantic import BaseModel
from typing import List, Optional


class GoalInput(BaseModel):
    goal: str
    key_results: List[str] = []


class ValidationCheck(BaseModel):
    name: str
    passed: bool
    message: str


class ValidationResult(BaseModel):
    is_valid: bool
    score: int
    checks: List[ValidationCheck]
    suggestions: List[str] = []


class DecomposeInput(BaseModel):
    goal: str


class DecomposeResult(BaseModel):
    company: str
    teams: List[str]
    individual: str
    reasoning: str
    traceability_score: int


class Task(BaseModel):
    text: str
    type: str


class Employee(BaseModel):
    name: str
    role: str
    skills: List[str]


class MatchInput(BaseModel):
    tasks: List[Task]
    employees: List[Employee]


class Assignment(BaseModel):
    task: str
    employee: str
    reason: str


class MatchResult(BaseModel):
    assignments: List[Assignment]
    confidence: int
