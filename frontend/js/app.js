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
        document.querySelectorAll('.step-item').forEach(s => s.classList.remove('active'));
        step.classList.add('active');
        document.querySelectorAll('.ai-panel').forEach(p => p.classList.remove('active'));
        document.getElementById('panel-' + stepName).classList.add('active');
    });
});

// === API URL ===
// Через Docker/nginx проксируется на backend
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
        renderValidationResult(data);
    } catch (e) {
        // Fallback для демо без backend
        renderValidationResult(getMockValidation(goal, krs));
    }
}

function renderValidationResult(data) {
    const box = document.getElementById('validation-result');
    box.className = 'result-box ' + (data.is_valid ? 'result-success' : data.score > 50 ? 'result-warning' : 'result-error');
    
    let html = `<div class="result-title">${data.is_valid ? '✅ Цель корректна' : '⚠️ Цель требует доработки'}</div>`;
    html += `<div style="margin-bottom: 12px; font-size: 13px; color: #555;">Оценка: <strong>${data.score}/100</strong></div>`;
    html += '<ul class="result-list">';
    
    data.checks.forEach(check => {
        const icon = check.passed ? '✅' : '❌';
        html += `<li><span class="icon">${icon}</span><div><strong>${check.name}:</strong> ${check.message}</div></li>`;
    });
    
    html += '</ul>';
    
    if (data.suggestions && data.suggestions.length > 0) {
        html += '<div style="margin-top: 12px; padding-top: 12px; border-top: 1px dashed #ccc;">';
        html += '<strong>💡 Рекомендации:</strong><ul style="margin-top: 8px; padding-left: 20px; font-size: 13px; color: #555;">';
        data.suggestions.forEach(s => html += `<li>${s}</li>`);
        html += '</ul></div>';
    }
    
    box.innerHTML = html;
}

function getMockValidation(goal, krs) {
    const checks = [];
    let score = 100;
    const suggestions = [];

    // Specific
    const vagueWords = ['повысить', 'улучшить', 'оптимизировать', 'эффективность', 'качество'];
    const hasVague = vagueWords.some(w => goal.toLowerCase().includes(w));
    if (hasVague) {
        checks.push({ name: 'Конкретность', passed: false, message: 'Обнаружены расплывчатые формулировки ("повысить", "улучшить" и т.д.)' });
        score -= 25;
        suggestions.push('Замените "повысить эффективность" на конкретную метрику, например "сократить время обработки заказов на 20%"');
    } else {
        checks.push({ name: 'Конкретность', passed: true, message: 'Цель сформулирована конкретно' });
    }

    // Measurable
    const hasNumbers = /\d/.test(goal) || krs.some(kr => /\d/.test(kr));
    if (!hasNumbers) {
        checks.push({ name: 'Измеримость', passed: false, message: 'Отсутствуют числовые метрики' });
        score -= 20;
        suggestions.push('Добавьте количественные показатели (%, шт., дни, руб.)');
    } else {
        checks.push({ name: 'Измеримость', passed: true, message: 'Присутствуют числовые метрики' });
    }

    // Time-bound
    const hasTime = /\b(202[5-9]|до\s+\w+|квартал|год|месяц|недел|день|Q[1-4])\b/i.test(goal + ' ' + krs.join(' '));
    if (!hasTime) {
        checks.push({ name: 'Ограниченность по времени', passed: false, message: 'Не указан срок достижения' });
        score -= 15;
        suggestions.push('Укажите дедлайн: "до конца Q3 2025" или "в течение 6 месяцев"');
    } else {
        checks.push({ name: 'Ограниченность по времени', passed: true, message: 'Срок указан' });
    }

    // KR count
    if (krs.length < 2) {
        checks.push({ name: 'Key Results', passed: false, message: 'Добавьте минимум 2-3 ключевых результата' });
        score -= 15;
        suggestions.push('Рекомендуется 2-5 Key Results для каждой цели');
    } else {
        checks.push({ name: 'Key Results', passed: true, message: `Определено ${krs.length} ключевых результата` });
    }

    // Achievable
    checks.push({ name: 'Достижимость', passed: true, message: 'Цель выглядит реалистичной' });

    return {
        is_valid: score >= 70,
        score: Math.max(0, score),
        checks,
        suggestions
    };
}

// === Декомпозиция ===
async function decomposeGoal() {
    const goal = document.getElementById('goal-input').value.trim();
    
    if (!goal) {
        alert('Сначала введите цель на шаге 1');
        return;
    }

    document.getElementById('source-goal-text').textContent = goal;

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

function renderDecomposeResult(data) {
    document.getElementById('company-goal').textContent = data.company;
    document.getElementById('team-goal-a').textContent = data.teams[0] || '—';
    document.getElementById('team-goal-b').textContent = data.teams[1] || '—';
    document.getElementById('individual-goal').textContent = data.individual || '—';

    const box = document.getElementById('decompose-result');
    box.className = 'result-box result-info';
    box.innerHTML = `
        <div class="result-title">⚡ Цель декомпозирована</div>
        <p style="font-size: 13px; color: #555; margin-bottom: 12px;">${data.reasoning}</p>
        <div style="font-size: 12px; color: #888;">Связность: <strong>${data.traceability_score}%</strong></div>
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

// === Матчинг ===
async function matchEmployees() {
    const tasks = Array.from(document.querySelectorAll('.task-item')).map(t => ({
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

function renderMatchResult(data) {
    const box = document.getElementById('match-result');
    box.className = 'result-box result-success';

    let html = '<div class="result-title">🎯 Распределение задач</div>';
    html += '<ul class="result-list">';

    data.assignments.forEach(a => {
        const reason = a.reason ? `<br><span style="font-size: 11px; color: #888;">${a.reason}</span>` : '';
        html += `<li>
            <span class="icon">👤</span>
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

    // Подсветить карточки сотрудников
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
    // Проверка связи с backend
    fetch(`${API_URL}/health`).catch(() => {
        console.log('Backend недоступен, используется демо-режим');
    });
});
