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
    diffPayload: null,
    currentDecomposition: null,
    breakdownTeamId: null,
    subtaskTeamMap: {},
    pendingDecomposeData: null,
    user: null,
    employee: null,
};

// === API URL ===
const API_URL = window.location.origin;

function authHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? { 'Authorization': 'Bearer ' + token } : {};
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
}

function getTeamName(teamId) {
    if (!teamId) return '—';
    const t = appState.teams.find(tm => tm.id === teamId);
    return t ? t.name : teamId.substring(0, 8);
}

async function initAuth() {
    const userStr = localStorage.getItem('user');
    if (userStr) {
        appState.user = JSON.parse(userStr);
    }
    try {
        const res = await fetch(`${API_URL}/api/auth/me`, { headers: { ...authHeaders() } });
        if (!res.ok) throw new Error('auth failed');
        const data = await res.json();
        appState.user = data.user;
        appState.employee = data.employee;
        localStorage.setItem('user', JSON.stringify(data.user));
        updateUIForRole();
    } catch (e) {
        console.error('Auth init failed', e);
        logout();
    }
}

function updateUIForRole() {
    const user = appState.user;
    if (!user) return;
    const roleLabels = { employee: 'Сотрудник', dept_head: 'Руководитель отдела', director: 'Руководитель направления' };
    document.getElementById('header-user-name').textContent = user.name + ' (' + roleLabels[user.role] + ')';
    document.getElementById('header-user-avatar').textContent = user.name.split(' ').map(p => p[0]).join('').substring(0, 2);
    document.getElementById('profile-name').textContent = user.name;
    document.getElementById('profile-position').textContent = roleLabels[user.role];

    // Сотрудник
    if (user.role === 'employee') {
        document.getElementById('tab-btn-kpi').textContent = 'МОИ ЗАДАЧИ';
        document.getElementById('tab-btn-ai-assistant').style.display = 'none';
        document.getElementById('btn-manage-employees').style.display = 'none';
        document.getElementById('btn-new-report').style.display = 'inline-flex';
        // Скрываем кнопки редактирования целей
        document.querySelectorAll('.btn-validate, .btn-decompose, .btn-generate-tasks, .btn-assign, .btn-rollback').forEach(el => el.style.display = 'none');
    }

    // Руководитель отдела
    if (user.role === 'dept_head') {
        document.getElementById('tab-btn-ai-assistant').style.display = 'none';
        document.getElementById('btn-manage-employees').style.display = 'inline-flex';
        document.getElementById('btn-new-report').style.display = 'none';
        // Скрываем кнопки director'а
        document.querySelectorAll('.btn-validate, .btn-generate-tasks, .btn-rollback').forEach(el => el.style.display = 'none');
    }

    // Director
    if (user.role === 'director') {
        document.getElementById('btn-manage-employees').style.display = 'none';
        document.getElementById('btn-new-report').style.display = 'none';
    }
}

function requireRole(...roles) {
    if (!appState.user || !roles.includes(appState.user.role)) {
        alert('Недостаточно прав');
        return false;
    }
    return true;
}

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
        const response = await fetch(`${API_URL}/api/goals`, { headers: { ...authHeaders() } });
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
        const response = await fetch(`${API_URL}/api/goals/${goalId}`, { headers: { ...authHeaders() } });
        const goal = await response.json();

        appState.currentGoalData = goal;
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
            // Сохраняем задачи цели
            appState.currentGoalTasks = goal.tasks || [];
            populateMatchTeamSelect(goal);
            // Если команда уже выбрана — фильтруем
            const teamSelect = document.getElementById('match-team-select');
            if (teamSelect && teamSelect.value) {
                onMatchTeamChange();
            } else {
                document.getElementById('tasks-list-editable').innerHTML = '';
                document.getElementById('employees-grid').innerHTML = '';
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
        const res = await fetch(`${API_URL}/api/upload-document`, { method: 'POST', headers: { ...authHeaders() }, body: formData });
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
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/reset-chat`, { method: 'POST', headers: { ...authHeaders() } });
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
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
        const res = await fetch(`${API_URL}/api/teams`, { headers: { ...authHeaders() } });
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

function collectCurrentTeamTexts() {
    const nodes = document.querySelectorAll('#team-level-container .node-text-editable');
    const texts = [];
    nodes.forEach(n => {
        texts.push({ team_name: n.previousElementSibling ? n.previousElementSibling.textContent : 'Команда', text: n.textContent.trim() });
    });
    return texts;
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

    // Если уже есть декомпозиция, собираем текущие тексты для diff
    const hasExisting = document.querySelectorAll('#team-level-container .node-text-editable').length > 0;
    let oldTeams = null;
    if (hasExisting) {
        oldTeams = collectCurrentTeamTexts();
    }

    appState.decomposed = true;
    document.getElementById('source-goal-text').textContent = goalText;
    document.getElementById('decompose-result').classList.remove('hidden');
    document.getElementById('decompose-result').innerHTML = '<div class="loading-text">Декомпозируем цель...</div>';

    try {
        const response = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/decompose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() }
        });
        const data = await response.json();

        if (oldTeams && oldTeams.length > 0) {
            appState.pendingDecomposeData = data;
            showDecomposeDiff(oldTeams, data);
            document.getElementById('decompose-result').innerHTML = '';
            return;
        }

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
    appState.currentDecomposition = data;

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

function showDecomposeDiff(oldTeams, newData) {
    let html = '<div class="diff-assign-row header"><div>Команда</div><div>Текущая версия</div><div>Новая версия</div></div>';
    const newTeams = newData.teams || [];
    const maxLen = Math.max(oldTeams.length, newTeams.length);
    for (let i = 0; i < maxLen; i++) {
        const oldT = oldTeams[i] || { team_name: '—', text: '—' };
        const newT = newTeams[i] || { team_name: '—', text: '—' };
        const newText = (typeof newT === 'object') ? (newT.text || '') : newT;
        const oldText = oldT.text || '—';
        html += `<div class="diff-assign-row">
            <div><strong>${escapeHtml(oldT.team_name)}</strong></div>
            <div class="old-val">${escapeHtml(oldText)}</div>
            <div class="new-val">${escapeHtml(newText)}</div>
        </div>`;
    }

    document.getElementById('diff-old').textContent = '';
    document.getElementById('diff-new').textContent = '';
    document.getElementById('diff-kr-section').classList.add('hidden');
    document.getElementById('diff-assign-section').classList.remove('hidden');
    document.getElementById('diff-assign-table').innerHTML = html;

    document.querySelector('#diff-modal .modal-header h3').textContent = 'ИИ предлагает новую декомпозицию';
    const acceptBtn = document.querySelector('#diff-modal .modal-footer .btn-primary');
    acceptBtn.onclick = applyDecomposeDiff;
    acceptBtn.textContent = 'Принять новую декомпозицию';
    document.getElementById('diff-modal').classList.remove('hidden');
}

function applyDecomposeDiff() {
    if (!appState.pendingDecomposeData) {
        closeDiffModal();
        return;
    }
    const data = appState.pendingDecomposeData;
    renderDecomposeResult({
        company: data.company,
        teams: data.teams,
        individual: data.individual,
        reasoning: data.reasoning,
        traceability_score: data.traceability_score
    });
    appState.pendingDecomposeData = null;
    closeDiffModal();
}

// === Матчинг (ручное распределение) ===
async function loadEmployees() {
    try {
        const res = await fetch(`${API_URL}/api/employees`, { headers: { ...authHeaders() } });
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

function populateMatchTeamSelect(goal) {
    const select = document.getElementById('match-team-select');
    if (!select) return;
    select.innerHTML = '<option value="">-- Выберите команду --</option>';

    // Берём команды из декомпозиции
    const decomps = goal.decompositions || [];
    if (decomps.length === 0) return;
    const teams = decomps[decomps.length - 1].team_goals || [];

    teams.forEach((t, idx) => {
        const name = (typeof t === 'object') ? (t.team_name || 'Команда') : 'Команда';
        const teamId = appState.teams[idx] ? appState.teams[idx].id : '';
        if (teamId) {
            select.innerHTML += `<option value="${teamId}">${escapeHtml(name)}</option>`;
        }
    });
}

async function onMatchTeamChange() {
    const select = document.getElementById('match-team-select');
    const teamId = select ? select.value : '';
    const taskSection = document.getElementById('team-task-section');

    if (!teamId) {
        document.getElementById('employees-grid').innerHTML = '';
        document.getElementById('tasks-list-editable').innerHTML = '';
        if (taskSection) taskSection.style.display = 'none';
        return;
    }

    // Показываем секцию задачи команды
    if (taskSection) taskSection.style.display = 'block';

    // Находим задачу команды из декомпозиции
    const goal = appState.currentGoalData;
    let teamTaskText = '';
    let teamName = '';
    if (goal && goal.decompositions && goal.decompositions.length > 0) {
        const decomp = goal.decompositions[goal.decompositions.length - 1];
        const teamGoals = decomp.team_goals || [];
        // Ищем по team_id через appState.teams
        const teamIdx = appState.teams.findIndex(t => t.id === teamId);
        if (teamIdx >= 0 && teamGoals[teamIdx]) {
            const tg = teamGoals[teamIdx];
            teamTaskText = (typeof tg === 'object') ? (tg.text || '') : tg;
            teamName = (typeof tg === 'object') ? (tg.team_name || '') : '';
        }
    }

    document.getElementById('team-task-display').textContent = teamTaskText || '—';
    appState.currentTeamTask = teamTaskText;
    appState.currentTeamName = teamName;
    appState.currentMatchTeamId = teamId;

    // Обновляем кнопку
    const existingTasks = (appState.currentGoalTasks || []).filter(t => t.team_id === teamId);
    const btn = document.getElementById('btn-breakdown-team');
    if (existingTasks.length > 0) {
        btn.textContent = 'Перегенерировать подзадачи';
    } else {
        btn.textContent = 'Разбить на подзадачи';
    }

    // Загружаем сотрудников команды
    try {
        const res = await fetch(`${API_URL}/api/teams/${teamId}/employees`, { headers: { ...authHeaders() } });
        const emps = await res.json();
        appState.currentMatchEmployees = emps;
        renderEmployeeCardsForMatch(emps);
    } catch (e) {
        console.error('Ошибка загрузки сотрудников команды:', e);
    }

    // Показываем существующие подзадачи
    renderEditableTasks(existingTasks);
}

async function runBreakdownForTeam() {
    const teamId = appState.currentMatchTeamId;
    const teamName = appState.currentTeamName;
    const taskText = appState.currentTeamTask;
    if (!teamId || !taskText) {
        alert('Выберите команду с задачей');
        return;
    }

    const teamObj = appState.teams.find(t => t.id === teamId);
    const specialization = teamObj ? teamObj.specialization : '';

    // Собираем текущие subtask'и для diff
    const existingTasks = (appState.currentGoalTasks || []).filter(t => t.team_id === teamId);
    const oldSubtasks = existingTasks.map(t => t.text);

    const btn = document.getElementById('btn-breakdown-team');
    const loading = document.getElementById('breakdown-loading');
    btn.style.display = 'none';
    loading.style.display = 'block';

    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/breakdown-team`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ team_id: teamId, team_name: teamName, team_task: taskText, specialization })
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();

        if (oldSubtasks.length > 0) {
            // Показываем diff
            appState.pendingBreakdownData = data;
            showBreakdownDiff(oldSubtasks, data.subtasks);
        } else {
            // Сразу применяем
            await applyBreakdownResult(data);
        }
    } catch (e) {
        alert('Ошибка разбиения: ' + e.message);
    } finally {
        btn.style.display = 'inline-block';
        loading.style.display = 'none';
    }
}

function showBreakdownDiff(oldSubtasks, newSubtasks) {
    let html = '<div class="diff-assign-row header"><div>№</div><div>Текущая версия</div><div>Новая версия</div></div>';
    const maxLen = Math.max(oldSubtasks.length, newSubtasks.length);
    for (let i = 0; i < maxLen; i++) {
        const oldT = oldSubtasks[i] || '—';
        const newT = newSubtasks[i] || '—';
        html += `<div class="diff-assign-row">
            <div><strong>${i + 1}</strong></div>
            <div class="old-val">${escapeHtml(oldT)}</div>
            <div class="new-val">${escapeHtml(newT)}</div>
        </div>`;
    }

    document.getElementById('diff-old').textContent = '';
    document.getElementById('diff-new').textContent = '';
    document.getElementById('diff-kr-section').classList.add('hidden');
    document.getElementById('diff-assign-section').classList.remove('hidden');
    document.getElementById('diff-assign-table').innerHTML = html;

    document.querySelector('#diff-modal .modal-header h3').textContent = 'ИИ предлагает новую разбивку';
    const acceptBtn = document.querySelector('#diff-modal .modal-footer .btn-primary');
    acceptBtn.onclick = acceptBreakdownDiff;
    acceptBtn.textContent = 'Принять новую разбивку';
    document.getElementById('diff-modal').classList.remove('hidden');
}

async function acceptBreakdownDiff() {
    if (!appState.pendingBreakdownData) {
        closeDiffModal();
        return;
    }
    await applyBreakdownResult(appState.pendingBreakdownData);
    appState.pendingBreakdownData = null;
    closeDiffModal();
}

async function applyBreakdownResult(data) {
    // Обновляем currentGoalTasks
    await loadGoalDetails(appState.currentGoalId, 'match');
    // Выбираем ту же команду
    const select = document.getElementById('match-team-select');
    if (select && appState.currentMatchTeamId) {
        select.value = appState.currentMatchTeamId;
        onMatchTeamChange();
    }
}

function renderEmployeeCardsForMatch(employees) {
    const grid = document.getElementById('employees-grid');
    if (!grid) return;
    grid.innerHTML = '';
    employees.forEach(e => {
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

async function reloadTeamTasks() {
    if (!appState.currentGoalId) {
        alert('Сначала выберите цель');
        return;
    }
    await loadGoalDetails(appState.currentGoalId, 'match');
    onMatchTeamChange();
}

function renderMatchPanel() {
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

    // Используем текущих сотрудников команды (если на match-панели) или всех
    let allowedEmployees = appState.currentMatchEmployees || appState.employees;

    const empOptions = allowedEmployees.map(e =>
        `<option value="${e.id}" ${taskData && taskData.assigned_employee_id === e.id ? 'selected' : ''}>${escapeHtml(e.name)}</option>`
    ).join('');

    const typeLabel = taskData && taskData.type ? `<span class="task-type-label" style="font-size:11px;color:#64748b;background:#f1f5f9;padding:2px 6px;border-radius:4px;margin-right:6px;">${taskData.type}</span>` : '';

    row.innerHTML = `
        ${typeLabel}
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

// === AI Suggest Assignments ===
appState.pendingSuggestions = null;

async function suggestAssignments() {
    if (!appState.currentGoalId) {
        alert('Выберите цель');
        return;
    }
    const teamId = appState.currentMatchTeamId;
    if (!teamId) {
        alert('Выберите команду');
        return;
    }
    try {
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/suggest-assignments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ team_id: teamId })
        });
        if (!res.ok) throw new Error(await res.text());
        const data = await res.json();
        appState.pendingSuggestions = data.suggestions || [];

        // Показываем diff только для текущих задач команды
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
                headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
        const res = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/versions`, { headers: { ...authHeaders() } });
        const versions = await res.json();
        if (!versions || versions.length < 2) {
            alert('Нет предыдущей версии для отката');
            return;
        }
        // Берём предпоследнюю версию (последняя — текущее состояние)
        const target = versions[1];
        const rollbackRes = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
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
    appState.pendingBreakdownData = null;
    // Восстанавливаем стандартный обработчик
    const acceptBtn = document.querySelector('#diff-modal .modal-footer .btn-primary');
    acceptBtn.onclick = acceptDiff;
    acceptBtn.textContent = 'Принять изменения';
    document.querySelector('#diff-modal .modal-header h3').textContent = 'ИИ предлагает изменения';
    document.getElementById('diff-assign-section').classList.add('hidden');
}

// === Отчеты ===

async function loadReports() {
    const container = document.getElementById('reports-list');
    if (!container) return;
    try {
        const res = await fetch(`${API_URL}/api/reports`, { headers: { ...authHeaders() } });
        const reports = await res.json();
        renderReports(reports);
    } catch (e) {
        console.error('Ошибка загрузки отчетов', e);
    }
}

function renderReports(reports) {
    const container = document.getElementById('reports-list');
    if (!reports || reports.length === 0) {
        container.innerHTML = '<p style="color:#888; text-align:center; padding: 40px;">Нет отчетов</p>';
        return;
    }
    const statusLabels = { draft: 'Черновик', pending: 'На проверке', approved: 'Одобрен', rejected: 'Отклонен' };
    const statusColors = { draft: '#888', pending: '#f59e0b', approved: '#16a34a', rejected: '#dc2626' };
    const statusClasses = { draft: 'status-draft', pending: 'status-pending', approved: 'status-approved', rejected: 'status-rejected' };
    let html = '<table style="width:100%; border-collapse: collapse; font-size: 13px;"><thead><tr style="background:#f1f5f9;"><th style="padding:10px; text-align:left;">Содержание</th><th style="padding:10px; text-align:left;">Автор</th><th style="padding:10px; text-align:left;">Дата</th><th style="padding:10px; text-align:left;">Статус</th><th style="padding:10px; text-align:left;">ИИ оценка</th><th style="padding:10px; text-align:left;">Действия</th></tr></thead><tbody>';
    reports.forEach(r => {
        const stLabel = statusLabels[r.status] || r.status;
        const stClass = statusClasses[r.status] || 'status-draft';
        const dateStr = r.created_at ? new Date(r.created_at).toLocaleString('ru-RU') : '—';
        const authorStr = r.author_name || '—';
        const attachmentHtml = r.attachment_url ? `<br><a href="${r.attachment_url}" target="_blank" download style="font-size:12px; color:#0066CC;">📎 Скачать PDF</a>` : '';
        html += `<tr style="border-bottom:1px solid #e2e8f0;">
            <td style="padding:10px;">${escapeHtml(r.content.substring(0, 60))}${r.content.length>60?'...':''}${attachmentHtml}</td>
            <td style="padding:10px;">${escapeHtml(authorStr)}</td>
            <td style="padding:10px;">${dateStr}</td>
            <td style="padding:10px;"><span class="status-badge ${stClass}">${stLabel}</span></td>
            <td style="padding:10px;">${r.ai_score !== null ? r.ai_score + '/100' : '—'}</td>
            <td style="padding:10px;">`;
        // Просмотр отчета (все роли)
        html += `<button class="btn-secondary" style="padding:4px 8px; font-size:12px;" onclick="viewReport('${r.id}')">Просмотр</button>`;
        if (appState.user && appState.user.role === 'employee' && r.status === 'draft') {
            html += `<button class="btn-secondary" style="padding:4px 8px; font-size:12px; margin-left:4px;" onclick="aiCheckReport('${r.id}')">Проверить ИИ</button>
                     <button class="btn-primary" style="padding:4px 8px; font-size:12px; margin-left:4px;" onclick="submitReportById('${r.id}')">Отправить</button>`;
        }
        if ((appState.user && (appState.user.role === 'dept_head' || appState.user.role === 'director')) && r.status === 'pending') {
            html += `<button class="btn-primary" style="padding:4px 8px; font-size:12px; margin-left:4px;" onclick="reviewReport('${r.id}', 'approved')">Одобрить</button>
                     <button class="btn-secondary" style="padding:4px 8px; font-size:12px; margin-left:4px;" onclick="reviewReport('${r.id}', 'rejected')">Отклонить</button>`;
        }
        html += `</td></tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function closeReportViewModal() {
    document.getElementById('report-view-modal').classList.add('hidden');
}

async function viewReport(reportId) {
    try {
        const res = await fetch(`${API_URL}/api/reports`, { headers: { ...authHeaders() } });
        const reports = await res.json();
        const r = reports.find(rep => rep.id === reportId);
        if (!r) return;
        const statusLabels = { draft: 'Черновик', pending: 'На проверке', approved: 'Одобрен', rejected: 'Отклонен' };
        const statusClasses = { draft: 'status-draft', pending: 'status-pending', approved: 'status-approved', rejected: 'status-rejected' };
        const stLabel = statusLabels[r.status] || r.status;
        const stClass = statusClasses[r.status] || 'status-draft';
        const dateStr = r.created_at ? new Date(r.created_at).toLocaleString('ru-RU') : '—';
        const authorStr = r.author_name || '—';

        let bodyHtml = `<div style="margin-bottom:12px;"><strong>Автор:</strong> ${escapeHtml(authorStr)}</div>`;
        bodyHtml += `<div style="margin-bottom:12px;"><strong>Дата создания:</strong> ${dateStr}</div>`;
        bodyHtml += `<div style="margin-bottom:12px;"><strong>Статус:</strong> <span class="status-badge ${stClass}">${stLabel}</span></div>`;
        if (r.attachment_url) {
            bodyHtml += `<div style="margin-bottom:12px;"><strong>Вложение:</strong> <a href="${r.attachment_url}" target="_blank" download style="color:#0066CC;">📎 Скачать PDF</a></div>`;
        }
        bodyHtml += `<hr style="border:0; border-top:1px solid #e2e8f0; margin:16px 0;">`;
        bodyHtml += `<div style="margin-bottom:12px;"><strong>Содержание:</strong></div>`;
        bodyHtml += `<div style="background:#f7f9fa; padding:12px; border-radius:6px; white-space:pre-wrap; margin-bottom:16px;">${escapeHtml(r.content)}</div>`;
        if (r.ai_score !== null) {
            bodyHtml += `<div style="margin-bottom:12px;"><strong>ИИ оценка:</strong> ${r.ai_score}/100</div>`;
            bodyHtml += `<div style="background:#fffbeb; padding:12px; border-radius:6px; border-left:4px solid #f59e0b; margin-bottom:16px;">${escapeHtml(r.ai_feedback)}</div>`;
        }
        if (r.review_comment) {
            bodyHtml += `<div style="margin-bottom:12px;"><strong>Комментарий проверяющего:</strong></div>`;
            bodyHtml += `<div style="background:#ecfdf5; padding:12px; border-radius:6px; border-left:4px solid #16a34a;">${escapeHtml(r.review_comment)}</div>`;
        }

        document.getElementById('report-view-body').innerHTML = bodyHtml;
        document.getElementById('report-view-modal').classList.remove('hidden');
    } catch (e) {
        console.error(e);
    }
}

async function loadMyTasksForReports() {
    const select = document.getElementById('report-task-select');
    if (!select) return;
    try {
        const res = await fetch(`${API_URL}/api/tasks`, { headers: { ...authHeaders() } });
        const tasks = await res.json();
        select.innerHTML = '<option value="">-- Выберите задачу --</option>';
        tasks.forEach(t => {
            select.innerHTML += `<option value="${t.id}">${escapeHtml(t.text.substring(0,60))}</option>`;
        });
    } catch (e) {
        console.error('Ошибка загрузки задач для отчетов', e);
    }
}

function openReportForm() {
    document.getElementById('report-form-section').style.display = 'block';
    loadMyTasksForReports();
}

function closeReportForm() {
    document.getElementById('report-form-section').style.display = 'none';
    document.getElementById('report-content').value = '';
    document.getElementById('report-ai-result').classList.add('hidden');
}

async function submitReport() {
    const taskId = document.getElementById('report-task-select').value;
    const content = document.getElementById('report-content').value.trim();
    const fileInput = document.getElementById('report-attachment');
    if (!taskId || !content) { alert('Выберите задачу и заполните содержание'); return; }
    try {
        const res = await fetch(`${API_URL}/api/reports`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ task_id: taskId, content })
        });
        if (!res.ok) throw new Error(await res.text());
        const report = await res.json();

        // Загружаем PDF если выбран
        if (fileInput && fileInput.files && fileInput.files[0]) {
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            await fetch(`${API_URL}/api/reports/${report.id}/upload`, {
                method: 'POST',
                headers: { ...authHeaders() },
                body: formData
            });
        }

        closeReportForm();
        loadReports();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

async function aiCheckReport(reportId) {
    try {
        const res = await fetch(`${API_URL}/api/reports/${reportId}/ai-check`, {
            method: 'POST',
            headers: { ...authHeaders() }
        });
        const data = await res.json();
        alert(`Оценка ИИ: ${data.score}/100\n${data.feedback}`);
        loadReports();
    } catch (e) {
        alert('Ошибка ИИ-проверки: ' + e.message);
    }
}

async function submitReportById(reportId) {
    try {
        const res = await fetch(`${API_URL}/api/reports/${reportId}/submit`, {
            method: 'POST',
            headers: { ...authHeaders() }
        });
        if (!res.ok) throw new Error(await res.text());
        loadReports();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

async function reviewReport(reportId, status) {
    const comment = prompt('Комментарий к проверке:');
    try {
        const res = await fetch(`${API_URL}/api/reports/${reportId}/review`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify({ status, comment: comment || '' })
        });
        if (!res.ok) throw new Error(await res.text());
        loadReports();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

// === Управление сотрудниками ===

function openEmployeeModal() {
    document.getElementById('employee-modal').classList.remove('hidden');
    loadEmployeeModalData();
}

function closeEmployeeModal() {
    document.getElementById('employee-modal').classList.add('hidden');
    hideEmployeeForm();
}

async function loadEmployeeModalData() {
    const table = document.getElementById('employees-table');
    try {
        const res = await fetch(`${API_URL}/api/employees`, { headers: { ...authHeaders() } });
        const emps = await res.json();
        let html = '<table style="width:100%; border-collapse:collapse; font-size:13px;"><thead><tr style="background:#f1f5f9;"><th style="padding:10px; text-align:left;">ФИО</th><th style="padding:10px; text-align:left;">Должность</th><th style="padding:10px; text-align:left;">Команда</th><th style="padding:10px; text-align:left;">Действия</th></tr></thead><tbody>';
        emps.forEach(e => {
            html += `<tr style="border-bottom:1px solid #e2e8f0;">
                <td style="padding:10px;">${escapeHtml(e.name)}</td>
                <td style="padding:10px;">${escapeHtml(e.role)}</td>
                <td style="padding:10px;">${escapeHtml(getTeamName(e.team_id))}</td>
                <td style="padding:10px;">
                    <button class="btn-secondary" style="padding:4px 8px; font-size:12px;" onclick="editEmployee('${e.id}', '${escapeHtml(e.name)}', '${escapeHtml(e.role)}', '${e.team_id||''}', '${escapeHtml((e.skills||[]).join(','))}', '${escapeHtml((e.projects_history||[]).join(','))}')">Редактировать</button>
                    <button class="btn-secondary" style="padding:4px 8px; font-size:12px; margin-left:4px; color:#c62828; border-color:#c62828;" onclick="deleteEmployee('${e.id}')">Удалить</button>
                </td>
            </tr>`;
        });
        html += '</tbody></table>';
        table.innerHTML = html;
    } catch (e) {
        table.innerHTML = '<p style="color:#c62828;">Ошибка загрузки</p>';
    }

    const teamSelect = document.getElementById('employee-team-select');
    try {
        const res = await fetch(`${API_URL}/api/teams`, { headers: { ...authHeaders() } });
        const teams = await res.json();
        teamSelect.innerHTML = '<option value="">-- Без команды --</option>';
        teams.forEach(t => {
            teamSelect.innerHTML += `<option value="${t.id}">${escapeHtml(t.name)}</option>`;
        });
    } catch (e) {}
}

function showEmployeeForm() {
    document.getElementById('employee-form').style.display = 'block';
    document.getElementById('employee-form-title').textContent = 'Добавить сотрудника';
    document.getElementById('employee-edit-id').value = '';
    document.getElementById('employee-name').value = '';
    document.getElementById('employee-role').value = '';
    document.getElementById('employee-skills').value = '';
    document.getElementById('employee-projects').value = '';
}

function hideEmployeeForm() {
    document.getElementById('employee-form').style.display = 'none';
}

function editEmployee(id, name, role, teamId, skills, projects) {
    document.getElementById('employee-form').style.display = 'block';
    document.getElementById('employee-form-title').textContent = 'Редактировать сотрудника';
    document.getElementById('employee-edit-id').value = id;
    document.getElementById('employee-name').value = name;
    document.getElementById('employee-role').value = role;
    document.getElementById('employee-team-select').value = teamId;
    document.getElementById('employee-skills').value = skills;
    document.getElementById('employee-projects').value = projects;
}

async function saveEmployee() {
    const id = document.getElementById('employee-edit-id').value;
    const body = {
        name: document.getElementById('employee-name').value,
        role: document.getElementById('employee-role').value,
        team_id: document.getElementById('employee-team-select').value || null,
        skills: document.getElementById('employee-skills').value.split(',').map(s => s.trim()).filter(Boolean),
        projects_history: document.getElementById('employee-projects').value.split(',').map(s => s.trim()).filter(Boolean),
    };
    try {
        const url = id ? `${API_URL}/api/employees/${id}` : `${API_URL}/api/employees`;
        const method = id ? 'PUT' : 'POST';
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json', ...authHeaders() },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(await res.text());
        hideEmployeeForm();
        loadEmployeeModalData();
        loadEmployees();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

async function deleteEmployee(id) {
    if (!confirm('Удалить сотрудника?')) return;
    try {
        const res = await fetch(`${API_URL}/api/employees/${id}`, {
            method: 'DELETE',
            headers: { ...authHeaders() }
        });
        if (!res.ok) throw new Error(await res.text());
        loadEmployeeModalData();
        loadEmployees();
    } catch (e) {
        alert('Ошибка: ' + e.message);
    }
}

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
    initAuth().then(() => {
        loadGoalsList('validate');
        loadGoalsList('decompose');
        loadGoalsList('match');
        loadTeams();
        loadEmployees();
        loadReports();
        loadMyTasksForReports();
    });

    fetch(`${API_URL}/health`, { headers: { ...authHeaders() } }).catch(() => {
        console.log('Backend недоступен, используется демо-режим');
    });
});
