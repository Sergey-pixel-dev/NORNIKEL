# Agent Instructions — Nornikel OKR AI Agent

## Tech Stack

- **Backend**: FastAPI (Python 3.12), SQLAlchemy 2.0 async, PostgreSQL 16 (asyncpg)
- **Frontend**: Vanilla JS + CSS, Nginx (Alpine)
- **LLM**: Local Ollama `phi4-mini:latest` (3.8B Q4_K_M) via HTTP `/api/chat`
- **DB Migrations**: Alembic
- **Docker**: Compose 3 services (postgres, backend python:3.12-slim, frontend nginx:alpine)

## Key Conventions

### Async Everything
All DB operations are async. Use `AsyncSession` from `app.db.database`. Never use sync SQLAlchemy sessions.

### LLM Integration Pattern
All AI functions go through `app.agent.ai_service`, which:
1. Loads `chat_history` from the goal
2. Calls `ollama_client` with timeout (35s)
3. Appends messages back to DB
4. Falls back to mock logic on exception/timeout

This ensures the UI works even if Ollama is down.

### Docker Networking (Arch Linux)
Backend accesses host Ollama via `host.docker.internal:11434`. Requires `extra_hosts: ["host.docker.internal:host-gateway"]` in compose because Arch Linux does not have built-in `host.docker.internal` resolution.

### Database Seed
On startup, `seed.py` populates:
- 4 teams (Цифровизация процессов, Данные и аналитика, Инфраструктура и DevOps, Орг. развитие и обучение)
- 6 employees linked to teams via `team_id` FK

If `teams` table already has rows, seed is skipped.

## Data Model

### Core Entities
- `Goal`: title, description, key_results[], is_valid, validation_score, validation_checks[], suggestions[], chat_history[]
- `GoalDecomposition`: company_goal, team_goals[] (JSON), individual_goal, reasoning, traceability_score
- `Task`: text, type (`team` | `individual` | `subtask` | `general`), order, assigned_employee_id, **team_id**
- `Employee`: name, role, skills[], projects_history[], **team_id** → teams
- `Team`: name, specialization, description
- `GoalVersion`: step, payload (JSON snapshot), created_at

### Important FKs
- `Task.goal_id` → `Goal.id`
- `Task.assigned_employee_id` → `Employee.id`
- `Employee.team_id` → `Team.id`
- `GoalDecomposition.goal_id` → `Goal.id`
- `GoalVersion.goal_id` → `Goal.id`

## Feature: Team Breakdown

### Flow
1. User validates a goal (creates `Goal` row)
2. User clicks "Разбить цель" → `POST /api/goals/{id}/decompose` → returns team goals
3. Frontend renders editable team nodes + radio selection list
4. User selects ONE team, clicks "Разбить на подзадачи"
5. Frontend calls `POST /api/goals/{id}/breakdown-team` with:
   - `team_id`, `team_name`, `team_task`, `specialization`
6. Backend:
   - Loads employees of that team (`get_employees_by_team`)
   - Calls LLM `breakdown_team_task_llm` with team task + employee list
   - Deletes old `subtask` tasks for this goal
   - Creates new `Task` rows with `type="subtask"`
   - Saves `GoalVersion` snapshot
7. Frontend receives subtasks, renders them under the selected team node
8. On Match panel, subtask rows show only employees from that team in the dropdown

### Diff for Decomposition Regenerations
If user edits team goal texts via `contenteditable` and clicks "Разбить цель" again:
- Frontend collects current texts (`collectCurrentTeamTexts`)
- Calls API, gets new decomposition
- Shows diff modal (old vs new per-team) before replacing
- User can accept or reject

### Frontend State
- `appState.subtaskTeamMap`: maps `task_id` → `team_id` so match panel can filter employees
- `appState.breakdownTeamId`: last selected team for breakdown
- `appState.pendingDecomposeData`: stores new decomposition when diff is shown

## API Endpoints Quick Reference

```
POST   /api/validate
POST   /api/ai-rewrite
POST   /api/upload-document
GET    /api/goals
GET    /api/goals/{id}
POST   /api/goals/{id}/decompose
POST   /api/goals/{id}/generate-tasks
POST   /api/goals/{id}/breakdown-team      # NEW: team breakdown
POST   /api/goals/{id}/suggest-assignments
POST   /api/goals/{id}/assign
POST   /api/goals/{id}/rollback
POST   /api/goals/{id}/reset-chat
GET    /api/teams
GET    /api/employees
GET    /api/teams/{id}/employees            # NEW: team-scoped employees
GET    /api/goals/{id}/tasks
POST   /api/tasks
PUT    /api/tasks/{id}
DELETE /api/tasks/{id}
```

## LLM Prompts

### Decomposition (`decompose_goal_llm`)
```
Разбей корпоративную цель на задачи для N команд...
Команда 1: <задача>
Команда 2: <задача>
Обоснование: <пояснение>
```

### Team Breakdown (`breakdown_team_task_llm`)
```
Разбей командную задачу на 3-5 конкретных подзадач с указанием технологий...
Подзадача 1: <текст>
Подзадача 2: <текст>
Обоснование: <пояснение>
```

### Assignment Suggestions (`suggest_assignments_llm`)
```
Распредели задачи по сотрудникам на основе их навыков...
Задача 1: <имя>
Задача 2: <имя>
Обоснование: <почему>
```

## Testing Notes

- If Ollama is unreachable, all AI endpoints fall back to mock data. The UI should still display results.
- Seed data is deterministic but UUIDs are random. Tests should not hardcode UUIDs.
- The `generate-tasks` endpoint creates `team` and `individual` tasks from decomposition. `breakdown-team` creates `subtask` tasks. They can coexist.
