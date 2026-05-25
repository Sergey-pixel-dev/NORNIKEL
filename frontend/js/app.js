// === Состояние приложения ===
const appState = {
    currentGoal: '',
    currentTasks: [],
    decomposed: false,
    validated: false
};

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

    // Если перешли извне на декомпозицию без цели — показать форму ввода
    if (stepName === 'decompose') {
        renderDecomposePanel();
    }
    // Если перешли извне на матчинг без задач — показать форму ввода
    if (stepName === 'match') {
        renderMatchPanel();
    }
}

// === API URL ===
const API_URL = window.location.origin;

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
        const response = await fetch(`${API_URL}/api/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ goal, key_results: krs })
        });
        const data = await response.json();
        renderValidationResult(data, goal);
    } catch (e) {
        renderValidationResult(getMockValidation(goal, krs), goal);
    }
}

function renderValidationResult(data, goal) {
    const box = document.getElementById('validation-result');
    box.className = 'result-box ' + (data.is_valid ? 'result-success' : data.score > 50 ? 'result-warning' : 'result-error');

    let html = '';

    // Предупреждение если цель не валидна
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

    // Кнопка перехода к декомпозиции (всегда показывается)
    html += `<div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid #ddd;">`;
    if (!data.is_valid) {
        html += `<div style="font-size: 12px; color: #888; margin-bottom: 10px;">Вы можете продолжить декомпозицию, но рекомендуется сначала устранить замечания.</div>`;
    }
    html += `<button class="btn-primary" onclick="goToDecompose('${escapeHtml(goal)}')">
        <span class="btn-icon">[2]</span> Перейти к декомпозиции
    </button>`;
    html += `</div>`;

    box.innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function goToDecompose(goal) {
    appState.currentGoal = goal;
    activateStep('decompose');
    // Автоматически запускаем декомпозицию
    runDecompose(goal);
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

    if (appState.currentGoal && appState.validated) {
        // Пришли из валидации — скрыть форму ввода, показать результаты
        goalInputSection.classList.add('hidden');
        resultSection.classList.remove('hidden');
    } else {
        // Пришли извне — показать форму ввода
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

    try {
        const response = await fetch(`${API_URL}/api/decompose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ goal })
        });
        const data = await response.json();
        renderDecomposeResult(data);
    } catch (e) {
        renderDecomposeResult(getMockDecompose(goal));
    }
}

// backward compatibility
function decomposeGoal() {
    if (appState.currentGoal && appState.validated) {
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

    // Формируем задачи для матчинга
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
        // Пришли из декомпозиции — показать автоматические задачи
        autoSection.classList.remove('hidden');
        manualSection.classList.add('hidden');
        renderTasksFromDecompose();
    } else {
        // Пришли извне — показать форму ручного ввода
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

    try {
        const response = await fetch(`${API_URL}/api/match`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tasks, employees })
        });
        const data = await response.json();
        renderMatchResult(data);
    } catch (e) {
        renderMatchResult(getMockMatch(tasks, employees));
    }
}

// backward compatibility
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
    fetch(`${API_URL}/health`).catch(() => {
        console.log('Backend недоступен, используется демо-режим');
    });
});
