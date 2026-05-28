// === Состояние приложения ===
const appState = {
    currentGoalId: null,
    currentGoal: '',
    currentTitle: '',
    currentTasks: [],
    decomposed: false,
    validated: false,
    teams: [],
    employees: [],
    diffPayload: null, // для хранения предложения ИИ
};

// === API URL ===
const API_URL = window.location.origin;

// === Табы ===
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
});

// === Свернуть/развернуть КПЭ ===
function toggleKpi(header) {
    header.classList.toggle('collapsed');
}

// === Добавить KR ===
function addKr() {
    const list = document.getElementById('kr-list');
    const count = list.children.length + 1;
    const div = document.createElement('div');
    div.className = 'kr-item';
    div.innerHTML = `<input type="text" class="field-input kr-input" placeholder="KR${count}: Измеримый результат...">`;
    list.appendChild(div);
}

function setKrs(krs) {
    const list = document.getElementById('kr-list');
    list.innerHTML = '';
    krs.forEach((kr, idx) => {
        const div = document.createElement('div');
        div.className = 'kr-item';
        div.innerHTML = `<input type="text" class="field-input kr-input" value="${escapeHtml(kr)}" placeholder="KR${idx+1}: Измеримый результат...">`;
        list.appendChild(div);
    });
}

function getKrs() {
    return Array.from(document.querySelectorAll('.kr-input')).map(i => i.value.trim()).filter(v => v);
}

// === Шаги ИИ-ассистента ===
document.querySelectorAll('.step-item').forEach(step => {
    step.addEventListener('click', () => {
        const stepName = step.dataset.step;
        activateStep(stepName);
    });
});

function activateStep(stepName) {
    document.querySelectorAll('.step-item').forEach(s => s.classList.remove('active'));
    document.querySelector('.step-item[data-step="' + stepName + '"]').classList.add('active');
    document.querySelectorAll('.ai-panel').forEach(p => p.classList.remove('active'));
    document.getElementById('panel-' + stepName).classList.add('active');

    loadGoalsList(stepName);

    if (stepName === 'decompose') {
        renderDecomposePanel();
    }
    if (stepName === 'match') {
        renderMatchPanel();
    }
}

// === Загрузка списка целей ===
async function loadGoalsList(stepName) {
    const selectId = 'goals-select-' + stepName;
    let select = document.getElementById(selectId);
    if (!select) return;

    try {
        const response = await fetch(`${API_URL}/api/goals`);
        const goals = await response.json();
        select.innerHTML = '<option value="">-- Выберите цель --</option>';
        goals.forEach(g => {
            const option = document.createElement('option');
            option.value = g.id;
            option.textContent = `${g.title} (оценка: ${g.validation_score})`;
            if (g.id === appState.currentGoalId) option.selected = true;
            select.appendChild(option);
        });
    } catch (e) {
        select.innerHTML = '<option value="">Ошибка загрузки</option>';
    }
}

function onGoalSelected(stepName, goalId) {
    if (!goalId) return;
    appState.currentGoalId = goalId;
    loadGoalDetails(goalId, stepName);
    updateResetChatButton();
}

function updateResetChatButton() {
    const btn = document.getElementById('btn-reset-chat');
    if (btn) {
        btn.style.display = appState.currentGoalId ? 'inline-flex' : 'none';
    }
}

async function loadGoalDetails(goalId, stepName) {
    try {
        const response = await fetch(`${API_URL}/api/goals/${goalId}`);
        const goal = await response.json();

        appState.currentGoal = goal.description;
        appState.currentTitle = goal.title;
        appState.validated = true;

        if (stepName === 'validate') {
            document.getElementById('goal-input').value = goal.description;
            if (goal.key_results && goal.key_results.length > 0) {
                setKrs(goal.key_results);
            }
            renderValidationResult({
                is_valid: goal.is_valid,
                score: goal.validation_score,
                checks: goal.validation_checks || [],
                suggestions: goal.suggestions || []
            }, goal.description, goal.id);
        }

        if (stepName === 'decompose') {
            document.getElementById('source-goal-text').textContent = goal.description;
            if (goal.decompositions && goal.decompositions.length > 0) {
                const d = goal.decompositions[goal.decompositions.length - 1];
                renderDecomposeResult({
                    company: d.company_goal,
                    teams: d.team_goals,
                    reasoning: d.reasoning,
                    traceability_score: d.traceability_score
                });
                appState.decomposed = true;
            } else {
                clearDecomposeResult();
            }
        }

        if (stepName === 'match') {
            // Загружаем задачи цели
            if (goal.tasks && goal.tasks.length > 0) {
                renderEditableTasks(goal.tasks);
            } else {
                document.getElementById('tasks-list-editable').innerHTML = '';
            }
        }
    } catch (e) {
        console.error('Ошибка загрузки цели:', e);
    }
}

// === Загрузка документа ===
async function uploadDocument() {
    const input = document.getElementById('goal-file-input');
    if (!input.files || !input.files[0]) {
        alert('Выберите файл');
        return;
    }
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_URL}/api/upload-document`, { method: 'POST', body: formData });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        document.getElementById('goal-input').value = data.extracted_text;
    } catch (e) {
        alert('Ошибка загрузки документа: ' + e.message);
    }
}

// === AI Rewrite ===
async function aiRewriteGoal() {
    const text = document.getElementById('goal-input').value.trim();
    if (!text) {
        alert('Введите цель');
        return;
    }
    const payload = { text };
    if (appState.currentGoalId) {
        payload.goal_id = appState.currentGoalId;
    }
    try {
        const res = await fetch(`${API_URL}/api/ai-rewrite`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        appState.diffPayload = data;
        showDiffModal(text, data.rewritten_goal, data.key_results);
    } catch (e) {
        alert('Ошибка ИИ-рерайта: ' + e.message);
    }
}

async function resetChat() {
    if (!appState.currentGoalId) {
        alert('Сначала выберите или создайте цель');
        return;
    }
    if (!confirm('Очистить историю чата ИИ для этой цели?')) return;
    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/reset-chat`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        alert('Контекст ИИ очищен');
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

function showDiffModal(oldText, newText, krs) {
    document.getElementById('diff-old').textContent = oldText || '—';
    document.getElementById('diff-new').textContent = newText || '—';
    const krSection = document.getElementById('diff-kr-section');
    const krList = document.getElementById('diff-kr-list');
    if (krs && krs.length > 0) {
        krSection.classList.remove('hidden');
        krList.innerHTML = krs.map(kr => `<li>${escapeHtml(kr)}</li>`).join('');
    } else {
        krSection.classList.add('hidden');
    }
    document.getElementById('diff-modal').classList.remove('hidden');
}

function closeDiffModal() {
    document.getElementById('diff-modal').classList.add('hidden');
    appState.diffPayload = null;
}

function acceptDiff() {
    if (!appState.diffPayload) return;
    document.getElementById('goal-input').value = appState.diffPayload.rewritten_goal;
    if (appState.diffPayload.key_results && appState.diffPayload.key_results.length > 0) {
        setKrs(appState.diffPayload.key_results);
    }
    closeDiffModal();
}

// === Валидация цели ===
async function validateGoal() {
    const goal = document.getElementById('goal-input').value.trim();
    const krs = getKrs();

    if (!goal) { alert('Введите цель'); return; }

    appState.currentGoal = goal;
    appState.validated = true;

    const resultBox = document.getElementById('validation-result');
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = '<div class="loading-text">Анализируем цель...</div>';

    try {
        const response = await fetch(`${API_URL}/api/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: goal, key_results: krs })
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}: ${await response.text()}`);
        const data = await response.json();
        appState.currentGoalId = data.goal_id;
        appState.currentTitle = data.title;
        renderValidationResult(data.validation, goal, data.goal_id);
        updateResetChatButton();
        await loadGoalsList('validate');
        await loadGoalsList('decompose');
        await loadGoalsList('match');
    } catch (e) {
        resultBox.innerHTML = `<div class="result-box result-error">
            <div class="result-title">[!] Ошибка соединения с сервером</div>
            <p style="font-size: 13px; color: #555;">${e.message}</p>
        </div>`;
    }
}

function renderValidationResult(data, goal, goalId) {
    const box = document.getElementById('validation-result');
    box.className = 'result-box ' + (data.is_valid ? 'result-success' : data.score > 50 ? 'result-warning' : 'result-error');

    let html = '';
    if (!data.is_valid) {
        html += `<div class="result-title" style="color: #c62828;">[!] Цель требует доработки</div>`;
        html += `<div style="margin-bottom: 12px; padding: 10px; background: #fff3e0; border-left: 3px solid #ff9800; font-size: 13px; color: #555;">
            <strong>Внимание:</strong> Цель не соответствует критериям SMART (оценка ${data.score}/100).
        </div>`;
    } else {
        html += `<div class="result-title">[OK] Цель корректна</div>`;
    }

    html += `<div style="margin-bottom: 12px; font-size: 13px; color: #555;">Оценка: <strong>${data.score}/100</strong></div>`;
    html += '<ul class="result-list">';
    data.checks.forEach(check => {
        const icon = check.passed ? '[+]' : '[-]';
        html += `<li><span class="icon">${icon}</span><div><strong>${check.name}:</strong> ${check.message}</div></li>`;
    });
    html += '</ul>';

    if (data.suggestions && data.suggestions.length > 0) {
        html += '<div style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #ccc;">';
        html += '<strong>Рекомендации:</strong><ul style="margin-top: 8px; padding-left: 20px; font-size: 13px; color: #555;">';
        data.suggestions.forEach(s => html += `<li>${s}</li>`);
        html += '</ul></div>';
    }

    html += `<div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #ddd;">`;
    const gid = goalId || appState.currentGoalId;
    if (gid) {
        html += `<button class="btn-primary" onclick="goToDecompose('${gid}')">
            <span class="btn-icon">[2]</span> Перейти к декомпозиции
        </button>`;
    }
    html += `</div>`;
    box.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function goToDecompose(goalId) {
    appState.currentGoalId = goalId;
    activateStep('decompose');
    loadGoalDetails(goalId, 'decompose');
}

// === Декомпозиция ===
async function loadTeams() {
    try {
        const res = await fetch(`${API_URL}/api/teams`);
        appState.teams = await res.json();
    } catch (e) {
        console.error('Ошибка загрузки команд:', e);
    }
}

function renderDecomposePanel() {
    const resultSection = document.getElementById('decompose-result-section');
    if (appState.currentGoalId && appState.validated) {
        resultSection.classList.remove('hidden');
    } else {
        resultSection.classList.add('hidden');
    }
}

function clearDecomposeResult() {
    document.getElementById('company-goal').textContent = '—';
    document.getElementById('team-level-container').innerHTML = '';
    document.getElementById('decompose-result').classList.add('hidden');
}

async function runDecomposeFromSelection() {
    if (!appState.currentGoalId) {
        alert('Выберите цель из списка');
        return;
    }
    const goalText = appState.currentGoal;
    if (!goalText) {
        alert('Цель пуста');
        return;
    }
    appState.decomposed = true;
    document.getElementById('source-goal-text').textContent = goalText;
    document.getElementById('decompose-result').classList.remove('hidden');
    document.getElementById('decompose-result').innerHTML = '<div class="loading-text">Декомпозируем цель...</div>';

    try {
        const response = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/decompose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        renderDecomposeResult({
            company: data.company,
            teams: data.teams,
            individual: data.individual,
            reasoning: data.reasoning,
            traceability_score: data.traceability_score
        });
    } catch (e) {
        console.error('Backend decompose failed', e);
        document.getElementById('decompose-result').innerHTML = '<div class="result-box result-error">Ошибка декомпозиции</div>';
    }
}

function renderDecomposeResult(data) {
    document.getElementById('company-goal').textContent = data.company;

    const container = document.getElementById('team-level-container');
    container.innerHTML = '';
    (data.teams || []).forEach((t, idx) => {
        const text = (typeof t === 'object') ? (t.text || t.team_name || JSON.stringify(t)) : t;
        const name = (typeof t === 'object') ? (t.team_name || 'Команда') : 'Команда';
        const node = document.createElement('div');
        node.className = 'tree-node';
        node.innerHTML = `<span class="node-badge">${escapeHtml(name)}</span><div class="node-text node-text-editable" contenteditable="true" data-index="${idx}">${escapeHtml(text)}</div>`;
        container.appendChild(node);
    });

    appState.currentTasks = (data.teams || []).map(t => {
        const text = (typeof t === 'object') ? (t.text || '') : t;
        return { text, type: 'team' };
    });

    const box = document.getElementById('decompose-result');
    box.className = 'result-box result-info';
    box.innerHTML = `
        <div class="result-title">[OK] Цель декомпозирована</div>
        <p style="font-size: 13px; color: #555; margin-bottom: 12px;">${escapeHtml(data.reasoning)}</p>
        <div style="font-size: 12px; color: #888;">Связность: <strong>${data.traceability_score}%</strong></div>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #ddd;">
            <button class="btn-primary" onclick="goToMatch()">
                <span class="btn-icon">[3]</span> Перейти к назначению исполнителей
            </button>
        </div>
    `;
}

function goToMatch() {
    activateStep('match');
}

// === Матчинг (ручное распределение) ===
async function loadEmployees() {
    try {
        const res = await fetch(`${API_URL}/api/employees`);
        appState.employees = await res.json();
        renderEmployeeCards();
    } catch (e) {
        console.error('Ошибка загрузки сотрудников:', e);
    }
}

function renderEmployeeCards() {
    const grid = document.getElementById('employees-grid');
    if (!grid) return;
    grid.innerHTML = '';
    appState.employees.forEach(e => {
        const card = document.createElement('div');
        card.className = 'employee-card';
        card.dataset.id = e.id;
        const initials = e.name.split(' ').map(p => p[0]).join('').substring(0, 2);
        const skills = (e.skills || []).map(s => `<span class="skill-tag hard">${escapeHtml(s)}</span>`).join('');
        const projects = (e.projects_history || []).map(p => `<li style="font-size:11px;color:#666;margin-top:2px;">• ${escapeHtml(p)}</li>`).join('');
        card.innerHTML = `
            <div style="display:flex;align-items:center;gap:10px;">
                <div class="employee-avatar">${initials}</div>
                <div class="employee-info">
                    <strong>${escapeHtml(e.name)}</strong>
                    <span>${escapeHtml(e.role)}</span>
                </div>
            </div>
            <div class="employee-skills">${skills}</div>
            <div style="margin-top:4px;">
                <div style="font-size:11px;color:#888;font-weight:600;">Проекты:</div>
                <ul style="padding-left:14px;margin:4px 0 0 0;">${projects || '<li style="font-size:11px;color:#999;">—</li>'}</ul>
            </div>
        `;
        grid.appendChild(card);
    });
}

function renderMatchPanel() {
    loadEmployees();
    if (appState.currentGoalId) {
        loadGoalDetails(appState.currentGoalId, 'match');
    }
}

// === CRUD Задач ===
function renderEditableTasks(tasks) {
    const container = document.getElementById('tasks-list-editable');
    container.innerHTML = '';
    tasks.forEach(t => addEditableTaskRow(t));
}

function addEditableTaskRow(taskData) {
    const container = document.getElementById('tasks-list-editable');
    const row = document.createElement('div');
    row.className = 'task-row';
    row.dataset.taskId = taskData ? taskData.id : '';

    const empOptions = appState.employees.map(e =>
        `<option value="${e.id}" ${taskData && taskData.assigned_employee_id === e.id ? 'selected' : ''}>${escapeHtml(e.name)}</option>`
    ).join('');

    row.innerHTML = `
        <input type="text" class="task-text-input" value="${escapeHtml(taskData ? taskData.text : '')}" placeholder="Описание задачи...">
        <select class="task-assign-select" onchange="highlightAssignedEmployees()">
            <option value="">— Не назначен —</option>
            ${empOptions}
        </select>
        <button class="task-delete" onclick="this.closest('.task-row').remove(); highlightAssignedEmployees();" title="Удалить">×</button>
    `;
    container.appendChild(row);
    highlightAssignedEmployees();
}

function highlightAssignedEmployees() {
    const selects = document.querySelectorAll('#tasks-list-editable .task-assign-select');
    const assignedIds = new Set();
    selects.forEach(s => { if (s.value) assignedIds.add(s.value); });

    document.querySelectorAll('.employee-card').forEach(card => {
        card.classList.toggle('assigned', assignedIds.has(card.dataset.id));
    });
}

function addTask() {
    addEditableTaskRow(null);
}

async function loadTasksFromDecomposition() {
    if (!appState.currentGoalId) {
        alert('Сначала выберите цель и выполните декомпозицию');
        return;
    }
    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/generate-tasks`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        const tasks = await res.json();
        renderEditableTasks(tasks);
    } catch (e) {
        alert('Ошибка генерации задач: ' + e.message);
    }
}

// === AI Suggest Assignments ===
appState.pendingSuggestions = null;

async function suggestAssignments() {
    if (!appState.currentGoalId) {
        alert('Выберите цель');
        return;
    }
    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/suggest-assignments`, { method: 'POST' });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        appState.pendingSuggestions = data.suggestions || [];

        // Показываем diff
        showAssignmentDiff(data.suggestions);
    } catch (e) {
        alert('Ошибка авторспределения: ' + e.message);
    }
}

function showAssignmentDiff(suggestions) {
    // Текущие назначения
    const rows = document.querySelectorAll('#tasks-list-editable .task-row');
    const current = {};
    rows.forEach(r => {
        const taskId = r.dataset.taskId;
        const empId = r.querySelector('.task-assign-select').value;
        const empName = empId ? r.querySelector('.task-assign-select option:checked').textContent : '—';
        current[taskId] = empName;
    });

    // Формируем таблицу diff
    let html = '<div class="diff-assign-row header"><div>Задача</div><div>Текущий</div><div>Предложение ИИ</div></div>';
    suggestions.forEach(s => {
        const oldVal = current[s.task_id] || '—';
        const newVal = s.employee_name || '—';
        html += `<div class="diff-assign-row">
            <div>${escapeHtml(s.task_text.substring(0, 40))}${s.task_text.length > 40 ? '…' : ''}</div>
            <div class="old-val">${escapeHtml(oldVal)}</div>
            <div class="new-val">${escapeHtml(newVal)}</div>
        </div>`;
    });

    document.getElementById('diff-old').textContent = '';
    document.getElementById('diff-new').textContent = '';
    document.getElementById('diff-kr-section').classList.add('hidden');
    document.getElementById('diff-assign-section').classList.remove('hidden');
    document.getElementById('diff-assign-table').innerHTML = html;

    // Меняем заголовок и обработчик кнопки Принять
    document.querySelector('#diff-modal .modal-header h3').textContent = 'ИИ предлагает назначения';
    const acceptBtn = document.querySelector('#diff-modal .modal-footer .btn-primary');
    acceptBtn.onclick = applySuggestedAssignments;
    acceptBtn.textContent = 'Принять назначения';

    document.getElementById('diff-modal').classList.remove('hidden');
}

function applySuggestedAssignments() {
    if (!appState.pendingSuggestions) {
        closeDiffModal();
        return;
    }
    appState.pendingSuggestions.forEach(s => {
        const row = document.querySelector(`.task-row[data-task-id="${s.task_id}"]`);
        if (row) {
            const select = row.querySelector('.task-assign-select');
            if (select && s.employee_id) {
                select.value = s.employee_id;
            }
        }
    });
    highlightAssignedEmployees();
    appState.pendingSuggestions = null;
    closeDiffModal();
}

async function saveAssignments() {
    if (!appState.currentGoalId) {
        alert('Выберите цель');
        return;
    }
    const rows = document.querySelectorAll('#tasks-list-editable .task-row');
    const payload = [];
    const tasksToCreate = [];

    for (const row of rows) {
        const text = row.querySelector('.task-text-input').value.trim();
        const empId = row.querySelector('.task-assign-select').value;
        const taskId = row.dataset.taskId;
        if (!text) continue;

        if (taskId) {
            // Обновляем существующую
            if (empId) {
                payload.push({ task_id: taskId, employee_id: empId });
            }
            await fetch(`${API_URL}/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
        } else {
            // Создаём новую
            tasksToCreate.push({ text, type: 'general', order: 0 });
        }
    }

    // Создаём новые задачи
    for (const t of tasksToCreate) {
        const res = await fetch(`${API_URL}/api/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ goal_id: appState.currentGoalId, ...t })
        });
        if (res.ok) {
            const created = await res.json();
            if (created.assigned_employee_id) {
                payload.push({ task_id: created.id, employee_id: created.assigned_employee_id });
            }
        }
    }

    // Сохраняем назначения
    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ assignments: payload })
        });
        if (!res.ok) throw new Error(await res.text());
        showMatchResult('Назначения сохранены');
    } catch (e) {
        alert('Ошибка сохранения: ' + e.message);
    }
}

function showMatchResult(message) {
    const box = document.getElementById('match-result');
    box.className = 'result-box result-success';
    box.classList.remove('hidden');
    box.innerHTML = `<div class="result-title">[OK] ${escapeHtml(message)}</div>`;
}

// === Rollback ===
async function rollbackLast() {
    if (!appState.currentGoalId) {
        alert('Выберите цель');
        return;
    }
    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/versions`);
        const versions = await res.json();
        if (!versions || versions.length < 2) {
            alert('Нет предыдущей версии для отката');
            return;
        }
        // Берём предпоследнюю версию (последняя — текущее состояние)
        const target = versions[1];
        const rollbackRes = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version_id: target.id })
        });
        if (!rollbackRes.ok) throw new Error(await rollbackRes.text());
        alert('Откат к прошлой версии выполнен');
        loadGoalDetails(appState.currentGoalId, 'match');
    } catch (e) {
        alert('Ошибка отката: ' + e.message);
    }
}

function closeDiffModal() {
    document.getElementById('diff-modal').classList.add('hidden');
    appState.diffPayload = null;
    appState.pendingSuggestions = null;
    // Восстанавливаем стандартный обработчик
    const acceptBtn = document.querySelector('#diff-modal .modal-footer .btn-primary');
    acceptBtn.onclick = acceptDiff;
    acceptBtn.textContent = 'Принять изменения';
    document.querySelector('#diff-modal .modal-header h3').textContent = 'ИИ предлагает изменения';
    document.getElementById('diff-assign-section').classList.add('hidden');
}

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
    loadGoalsList('validate');
    loadGoalsList('decompose');
    loadGoalsList('match');
    loadTeams();
    loadEmployees();

    fetch(`${API_URL}/health`).catch(() => {
        console.log('Backend недоступен, используется демо-режим');
    });
});
