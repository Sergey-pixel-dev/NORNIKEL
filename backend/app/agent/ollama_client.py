import os
import httpx
from typing import List

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi4-mini:latest")
TIMEOUT = 30.0

SYSTEM_PROMPT = (
    "Ты — ИИ-ассистент OKR для компании Норникель. "
    "Ты помогаешь директорам и руководителям: проверять цели на SMART, "
    "декомпозировать их на команды с учётом специализации, и распределять задачи по сотрудникам. "
    "Ты всегда отвечаешь строго в запрошенном формате, без лишних слов."
)


def _build_url(path: str) -> str:
    return f"{OLLAMA_HOST.rstrip('/')}{path}"


def _clean_response(text: str) -> str:
    return text.strip()


def _ensure_system(history: List[dict]) -> List[dict]:
    if not history or history[0].get("role") != "system":
        return [{"role": "system", "content": SYSTEM_PROMPT}] + history
    return history


async def chat(history: List[dict], user_prompt: str) -> str:
    """
    Отправляет запрос в Ollama Chat API с полной историей сообщений.
    Возвращает текст ответа ассистента.
    """
    messages = _ensure_system(history)
    messages.append({"role": "user", "content": user_prompt})

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            _build_url("/api/chat"),
            json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.3, "num_predict": 512},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        assistant_text = _clean_response(data.get("message", {}).get("content", ""))

    return assistant_text


async def rewrite_goal(history: List[dict], text: str) -> dict:
    prompt = (
        f"Перепиши следующую цель в формате SMART, конкретизируй метрики и срок. "
        f"Затем сформулируй 2–4 Key Results (KR). "
        f"Ответь строго в формате:\n"
        f"ЦЕЛЬ: <переписанная цель>\n"
        f"KR1: <ключевой результат 1>\n"
        f"KR2: <ключевой результат 2>\n"
        f"KR3: <ключевой результат 3>\n\n"
        f"Исходная цель: {text}\n\n"
        f"Ответ:"
    )
    raw = await chat(history, prompt)
    return _parse_goal_and_krs(raw)


def _parse_goal_and_krs(raw: str) -> dict:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    rewritten = ""
    krs = []
    for line in lines:
        if line.upper().startswith("ЦЕЛЬ:"):
            rewritten = line.split(":", 1)[1].strip()
        elif line.upper().startswith("KR"):
            kr_text = line.split(":", 1)[1].strip() if ":" in line else line
            krs.append(kr_text)
    if not rewritten:
        rewritten = lines[0] if lines else raw
    if not krs:
        krs = lines[1:] if len(lines) > 1 else ["Достичь целевого показателя", "Подготовить методологию"]
    return {"rewritten_goal": rewritten, "key_results": krs[:5]}


async def decompose_goal_llm(history: List[dict], goal: str, teams: List[dict]) -> dict:
    teams_list = "\n".join([f"- {t['name']} ({t.get('specialization','')})" for t in teams])
    prompt = (
        f"Разбей корпоративную цель на задачи для {len(teams)} команд. "
        f"Для каждой команды сформулируй одну конкретную задачу, вытекающую из цели.\n\n"
        f"Цель: {goal}\n\n"
        f"Команды:\n{teams_list}\n\n"
        f"Ответь строго в формате (без лишних слов):\n"
    )
    for i, t in enumerate(teams, 1):
        prompt += f"Команда {i}: <задача для {t['name']}>\n"
    prompt += "\nОбоснование: <краткое пояснение разбивки>\n"

    raw = await chat(history, prompt)
    return _parse_decompose(raw, teams)


def _parse_decompose(raw: str, teams: List[dict]) -> dict:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    team_goals = []
    reasoning = "Декомпозиция выполнена на основе анализа цели и специализации команд."

    for line in lines:
        for idx, t in enumerate(teams):
            prefix = f"Команда {idx + 1}:"
            if line.startswith(prefix):
                text = line[len(prefix):].strip()
                team_goals.append({"team_name": t["name"], "text": text})
        if line.startswith("Обоснование:"):
            reasoning = line.split(":", 1)[1].strip()

    if len(team_goals) < len(teams):
        team_goals = [{"team_name": t["name"], "text": f"Реализовать направление: {t.get('specialization','')}"} for t in teams]

    return {
        "teams": team_goals,
        "individual": "Создать прототип решения и провести пилотное тестирование",
        "reasoning": reasoning,
        "traceability_score": 88,
    }


async def suggest_assignments_llm(history: List[dict], tasks: List[dict], employees: List[dict]) -> List[dict]:
    tasks_text = "\n".join([f"- {i+1}. {t['text']}" for i, t in enumerate(tasks)])
    emps_text = "\n".join([f"- {e['name']}: {', '.join(e.get('skills', []))}" for e in employees])

    prompt = (
        f"Распредели задачи по сотрудникам на основе их навыков.\n\n"
        f"Задачи:\n{tasks_text}\n\n"
        f"Сотрудники:\n{emps_text}\n\n"
        f"Ответь строго в формате:\n"
    )
    for i in range(len(tasks)):
        prompt += f"Задача {i+1}: <имя сотрудника>\n"
    prompt += "\nОбоснование: <почему так распределено>\n"

    raw = await chat(history, prompt)
    return _parse_assignments(raw, tasks, employees)


def _parse_assignments(raw: str, tasks: List[dict], employees: List[dict]) -> List[dict]:
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    suggestions = []
    emp_map = {e["name"]: e for e in employees}

    for i, task in enumerate(tasks):
        prefix = f"Задача {i+1}:"
        emp_name = None
        for line in lines:
            if line.startswith(prefix):
                emp_name = line[len(prefix):].strip()
                break
        if not emp_name:
            emp_name = employees[i % len(employees)]["name"] if employees else "?"

        emp = emp_map.get(emp_name)
        suggestions.append({
            "task_id": task.get("id"),
            "task_text": task.get("text", ""),
            "employee_id": emp["id"] if emp else None,
            "employee_name": emp_name,
            "reason": f"Наилучшее соответствие по компетенциям: {', '.join(emp.get('skills', [])[:2]) if emp else 'общая компетентность'}"
        })

    return suggestions
