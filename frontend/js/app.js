// === Состояние приложения ===
const appState = {
    currentGoalId: null,
    currentGoal: '',
    currentTitle: '',
    currentTasks: [],
    decomposed: false,
    validated: false
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

    // Загружаем список целей на каждом шаге
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
    if (!select) {
        console.log('[loadGoalsList] select not found:', selectId);
        return;
    }

    try {
        console.log('[loadGoalsList] fetching goals for', stepName);
        const response = await fetch(`${API_URL}/api/goals`);
        const goals = await response.json();
        console.log('[loadGoalsList] got', goals.length, 'goals');

        select.innerHTML = '<option value="">-- Выберите цель --</option>';
        goals.forEach(g => {
            const option = document.createElement('option');
            option.value = g.id;
            option.textContent = `${g.title} (оценка: ${g.validation_score})`;
            if (g.id === appState.currentGoalId) {
                option.selected = true;
            }
            select.appendChild(option);
        });
    } catch (e) {
        console.error('[loadGoalsList] error:', e);
        select.innerHTML = '<option value="">Ошибка загрузки</option>';
    }
}

function onGoalSelected(stepName, goalId) {
    if (!goalId) return;
    appState.currentGoalId = goalId;
    loadGoalDetails(goalId, stepName);
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
            // Восстанавливаем KR если есть
            if (goal.suggestions && goal.suggestions.length > 0) {
                // Ничего не делаем, KR не хранятся отдельно пока
            }
            // Показываем результаты валидации
            renderValidationResult({
                is_valid: goal.is_valid,
                score: goal.validation_score,
                checks: goal.validation_checks || [],
                suggestions: goal.suggestions || []
            }, goal.description, goal.id);
        }

        if (stepName === 'decompose') {
            document.getElementById('decompose-goal-input').value = goal.description;
            if (goal.decompositions && goal.decompositions.length > 0) {
                const d = goal.decompositions[goal.decompositions.length - 1];
                renderDecomposeResult({
                    company: d.company_goal,
                    teams: d.team_goals,
                    individual: d.individual_goal,
                    reasoning: d.reasoning,
                    traceability_score: d.traceability_score
                });
                appState.decomposed = true;
            }
        }

        if (stepName === 'match') {
            if (goal.assignments && goal.assignments.length > 0) {
                const assignments = goal.assignments.map(a => ({
                    task: a.task_text,
                    employee: a.employee_name,
                    reason: a.reason
                }));
                renderMatchResult({ assignments, confidence: 87 });
            }
        }
    } catch (e) {
        console.error('Ошибка загрузки цели:', e);
    }
}

// === Валидация цели ===
async function validateGoal() {
    const goal = document.getElementById('goal-input').value.trim();
    const krInputs = document.querySelectorAll('.kr-input');
    const krs = Array.from(krInputs).map(i => i.value.trim()).filter(v => v);

    if (!goal) {
        alert('Введите цель');
        return;
    }

    appState.currentGoal = goal;
    appState.validated = true;

    const resultBox = document.getElementById('validation-result');
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = '<div class="loading-text">Анализируем цель...</div>';

    try {
        console.log('[validateGoal] sending request');
        const response = await fetch(`${API_URL}/api/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ description: goal, key_results: krs })
        });

        if (!response.ok) {
            const err = await response.text();
            throw new Error(`HTTP ${response.status}: ${err}`);
        }

        const data = await response.json();
        console.log('[validateGoal] saved goal_id:', data.goal_id);
        appState.currentGoalId = data.goal_id;
        appState.currentTitle = data.title;
        renderValidationResult(data.validation, goal, data.goal_id);

        // Обновляем списки целей на всех шагах
        console.log('[validateGoal] reloading goal lists...');
        await loadGoalsList('validate');
        await loadGoalsList('decompose');
        await loadGoalsList('match');
        console.log('[validateGoal] lists reloaded');
    } catch (e) {
        console.error('[validateGoal] error:', e);
        const resultBox = document.getElementById('validation-result');
        resultBox.innerHTML = `<div class="result-box result-error">
            <div class="result-title">[!] Ошибка соединения с сервером</div>
            <p style="font-size: 13px; color: #555;">Не удалось сохранить цель. Проверьте, что backend запущен (${e.message}).</p>
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
            <strong>Внимание:</strong> Цель не соответствует критериям SMART (оценка ${data.score}/100). Рекомендуется доработать формулировку перед каскадированием.
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

    // Кнопка перехода к декомпозиции
    html += `<div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #ddd;">`;
    if (!data.is_valid) {
        html += `<div style="font-size: 12px; color: #888; margin-bottom: 10px;">Вы можете продолжить декомпозицию, но рекомендуется сначала устранить замечания.</div>`;
    }
    const gid = goalId || appState.currentGoalId;
    if (gid) {
        html += `<button class="btn-primary" onclick="goToDecompose('${gid}')">
            <span class="btn-icon">[2]</span> Перейти к декомпозиции
        </button>`;
    } else {
        html += `<button class="btn-primary" onclick="goToDecomposeManual('${escapeHtml(goal)}')">
            <span class="btn-icon">[2]</span> Перейти к декомпозиции (демо)
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
    // Загружаем детали цели и запускаем декомпозицию
    loadGoalDetails(goalId, 'decompose').then(() => {
        if (appState.currentGoal) {
            runDecompose(appState.currentGoal);
        }
    });
}

function goToDecomposeManual(goal) {
    appState.currentGoal = goal;
    activateStep('decompose');
    renderDecomposePanel();
}

function getMockValidation(goal, krs) {
    const checks = [];
    let score = 100;
    const suggestions = [];

    const vagueWords = ['повысить', 'улучшить', 'оптимизировать', 'эффективность', 'качество'];
    const hasVague = vagueWords.some(w => goal.toLowerCase().includes(w));
    if (hasVague) {
        checks.push({ name: 'Конкретность', passed: false, message: 'Обнаружены расплывчатые формулировки ("повысить", "улучшить" и т.д.)' });
        score -= 25;
        suggestions.push('Замените "повысить эффективность" на конкретную метрику, например "сократить время обработки заказов на 20%"');
    } else {
        checks.push({ name: 'Конкретность', passed: true, message: 'Цель сформулирована конкретно' });
    }

    const hasNumbers = /\d/.test(goal) || krs.some(kr => /\d/.test(kr));
    if (!hasNumbers) {
        checks.push({ name: 'Измеримость', passed: false, message: 'Отсутствуют числовые метрики' });
        score -= 20;
        suggestions.push('Добавьте количественные показатели (%, шт., дни, руб.)');
    } else {
        checks.push({ name: 'Измеримость', passed: true, message: 'Присутствуют числовые метрики' });
    }

    const hasTime = /\b(202[5-9]|до\s+\w+|квартал|год|месяц|недел|день|Q[1-4])\b/i.test(goal + ' ' + krs.join(' '));
    if (!hasTime) {
        checks.push({ name: 'Ограниченность по времени', passed: false, message: 'Не указан срок достижения' });
        score -= 15;
        suggestions.push('Укажите дедлайн: "до конца Q3 2025" или "в течение 6 месяцев"');
    } else {
        checks.push({ name: 'Ограниченность по времени', passed: true, message: 'Срок указан' });
    }

    if (krs.length < 2) {
        checks.push({ name: 'Key Results', passed: false, message: 'Добавьте минимум 2-3 ключевых результата' });
        score -= 15;
        suggestions.push('Рекомендуется 2-5 Key Results для каждой цели');
    } else {
        checks.push({ name: 'Key Results', passed: true, message: `Определено ${krs.length} ключевых результата` });
    }

    checks.push({ name: 'Достижимость', passed: true, message: 'Цель выглядит реалистичной' });

    return {
        is_valid: score >= 70,
        score: Math.max(0, score),
        checks,
        suggestions
    };
}

// === Декомпозиция ===
function renderDecomposePanel() {
    const goalInputSection = document.getElementById('decompose-goal-input-section');
    const resultSection = document.getElementById('decompose-result-section');

    if (appState.currentGoalId && appState.validated) {
        goalInputSection.classList.add('hidden');
        resultSection.classList.remove('hidden');
    } else {
        goalInputSection.classList.remove('hidden');
        resultSection.classList.add('hidden');
    }
}

async function runDecompose(goal) {
    if (!goal) {
        goal = document.getElementById('decompose-goal-input')?.value.trim();
    }
    if (!goal) {
        alert('Введите цель');
        return;
    }

    appState.currentGoal = goal;
    appState.decomposed = true;

    document.getElementById('source-goal-text').textContent = goal;
    document.getElementById('decompose-goal-input-section')?.classList.add('hidden');
    document.getElementById('decompose-result-section')?.classList.remove('hidden');

    const resultBox = document.getElementById('decompose-result');
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = '<div class="loading-text">Декомпозируем цель...</div>';

    if (appState.currentGoalId) {
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
            return;
        } catch (e) {
            console.log('Backend decompose failed, using mock');
        }
    }

    renderDecomposeResult(getMockDecompose(goal));
}

function decomposeGoal() {
    if (appState.currentGoalId && appState.validated) {
        runDecompose(appState.currentGoal);
    } else {
        const input = document.getElementById('decompose-goal-input');
        runDecompose(input ? input.value.trim() : '');
    }
}

function renderDecomposeResult(data) {
    document.getElementById('company-goal').textContent = data.company;
    document.getElementById('team-goal-a').textContent = data.teams[0] || '—';
    document.getElementById('team-goal-b').textContent = data.teams[1] || '—';
    document.getElementById('individual-goal').textContent = data.individual || '—';

    appState.currentTasks = [
        { text: data.teams[0] || 'Задача команды A', type: 'Backend' },
        { text: data.teams[1] || 'Задача команды B', type: 'Frontend' },
        { text: data.individual || 'Индивидуальная задача', type: 'ML' }
    ];

    const box = document.getElementById('decompose-result');
    box.className = 'result-box result-info';
    box.innerHTML = `
        <div class="result-title">[OK] Цель декомпозирована</div>
        <p style="font-size: 13px; color: #555; margin-bottom: 12px;">${data.reasoning}</p>
        <div style="font-size: 12px; color: #888;">Связность: <strong>${data.traceability_score}%</strong></div>
        <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #ddd;">
            <button class="btn-primary" onclick="goToMatch()">
                <span class="btn-icon">[3]</span> Перейти к назначению исполнителей
            </button>
        </div>
    `;
}

function getMockDecompose(goal) {
    const teamGoals = [
        'Разработать и внедрить инструменты для автоматизации процессов',
        'Обеспечить обучение персонала и поддержку изменений'
    ];
    const individual = 'Создать прототип решения и провести пилотное тестирование';

    return {
        company: goal,
        teams: teamGoals,
        individual,
        reasoning: 'Цель разбита на командные направления с учётом функциональной специализации. Команда A отвечает за техническую реализацию, Команда B — за орг. поддержку.',
        traceability_score: 92
    };
}

function goToMatch() {
    activateStep('match');
    runMatch();
}

// === Матчинг ===
function renderMatchPanel() {
    const autoSection = document.getElementById('match-auto-section');
    const manualSection = document.getElementById('match-manual-section');

    if (appState.decomposed && appState.currentTasks.length > 0) {
        autoSection.classList.remove('hidden');
        manualSection.classList.add('hidden');
        renderTasksFromDecompose();
    } else {
        autoSection.classList.add('hidden');
        manualSection.classList.remove('hidden');
    }
}

function renderTasksFromDecompose() {
    const list = document.getElementById('tasks-list-auto');
    if (!list) return;
    list.innerHTML = '';
    appState.currentTasks.forEach((task, idx) => {
        const div = document.createElement('div');
        div.className = 'task-item';
        div.innerHTML = `
            <span class="task-text">${escapeHtml(task.text)}</span>
            <span class="task-badge ${task.type.toLowerCase()}">${escapeHtml(task.type)}</span>
        `;
        list.appendChild(div);
    });
}

async function runMatch() {
    if (appState.currentGoalId) {
        try {
            const resultBox = document.getElementById('match-result');
            resultBox.classList.remove('hidden');
            resultBox.innerHTML = '<div class="loading-text">Анализируем компетенции...</div>';

            const response = await fetch(`${API_URL}/api/goals/${appState.currentGoalId}/match`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await response.json();
            renderMatchResult(data);
            return;
        } catch (e) {
            console.log('Backend match failed, using mock');
        }
    }

    // Fallback
    const tasks = appState.currentTasks.length > 0
        ? appState.currentTasks
        : Array.from(document.querySelectorAll('#tasks-list-manual .task-item')).map(t => ({
            text: t.querySelector('.task-text').textContent,
            type: t.querySelector('.task-badge').textContent
        }));

    const employees = Array.from(document.querySelectorAll('.employee-card')).map(card => ({
        name: card.querySelector('.employee-info strong').textContent,
        role: card.querySelector('.employee-info span').textContent,
        skills: card.dataset.skills.split(',')
    }));

    const resultBox = document.getElementById('match-result');
    resultBox.classList.remove('hidden');
    resultBox.innerHTML = '<div class="loading-text">Анализируем компетенции...</div>';

    renderMatchResult(getMockMatch(tasks, employees));
}

function matchEmployees() {
    runMatch();
}

function renderMatchResult(data) {
    const box = document.getElementById('match-result');
    box.className = 'result-box result-success';

    let html = '<div class="result-title">[OK] Распределение задач</div>';
    html += '<ul class="result-list">';

    data.assignments.forEach(a => {
        const reason = a.reason ? `<br><span style="font-size: 11px; color: #888;">${a.reason}</span>` : '';
        html += `<li>
            <span class="icon">[>]</span>
            <div>
                <strong>${a.task}</strong> → <span style="color: #0066CC; font-weight: 600;">${a.employee}</span>
                ${reason}
            </div>
        </li>`;
    });

    html += '</ul>';

    if (data.confidence) {
        html += `<div style="margin-top: 12px; font-size: 12px; color: #888;">Уверенность модели: <strong>${data.confidence}%</strong></div>`;
    }

    box.innerHTML = html;

    document.querySelectorAll('.employee-card').forEach(card => {
        const name = card.querySelector('.employee-info strong').textContent;
        const isMatched = data.assignments.some(a => a.employee === name);
        card.classList.toggle('matched', isMatched);
    });
}

function getMockMatch(tasks, employees) {
    const skillMap = {
        'ML': 'Петров С.А.',
        'Frontend': 'Иванова К.М.',
        'Backend': 'Сидоров Д.В.'
    };

    const assignments = tasks.map(t => ({
        task: t.text,
        employee: skillMap[t.type] || employees[0].name,
        reason: `Наилучшее соответствие по hard skills: ${t.type}`
    }));

    return { assignments, confidence: 87 };
}

// === Инициализация ===
document.addEventListener('DOMContentLoaded', () => {
    // Загружаем списки целей на всех шагах при старте
    loadGoalsList('validate');
    loadGoalsList('decompose');
    loadGoalsList('match');

    fetch(`${API_URL}/health`).catch(() => {
        console.log('Backend недоступен, используется демо-режим');
    });
});
