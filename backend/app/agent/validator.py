"""
Модуль валидации целей OKR.
Проверяет цели на соответствие SMART-критериям и корпоративным правилам.
"""

import re
from typing import List
from app.models import ValidationResult, ValidationCheck


# Расплывчатые слова, которые делают цель неконкретной
VAGUE_WORDS = [
    "повысить", "улучшить", "оптимизировать", "эффективность", "качество",
    "стремиться", "пытаться", "понять", "изучить", "разобраться",
    "сделать лучше", "улучшить качество", "повысить уровень"
]

# Слова, указывающие на измеримость
MEASURE_INDICATORS = [
    "%", "процент", "руб", "usd", "шт", "единиц", "дней", "часов",
    "раз", "кратно", "в", "до", "от", "на"
]

# Временные маркеры
TIME_MARKERS = [
    "202", "год", "квартал", "q", "месяц", "недел", "день",
    "до конца", "в течение", "к", "не позднее", "срок"
]


def validate_goal(goal: str, key_results: List[str]) -> ValidationResult:
    """
    Проверяет цель на соответствие критериям SMART и корпоративным нормам.
    """
    checks = []
    suggestions = []
    score = 100

    goal_lower = goal.lower()
    combined_text = (goal + " " + " ".join(key_results)).lower()

    # 1. Конкретность (Specific)
    vague_found = [w for w in VAGUE_WORDS if w in goal_lower]
    if vague_found:
        checks.append(ValidationCheck(
            name="Конкретность (Specific)",
            passed=False,
            message=f"Обнаружены расплывчатые формулировки: {', '.join(vague_found[:3])}"
        ))
        score -= 25
        suggestions.append(
            f"Замените расплывчатые слова на конкретные метрики. "
            f"Например, вместо '{vague_found[0]}' укажите точный показатель."
        )
    else:
        checks.append(ValidationCheck(
            name="Конкретность (Specific)",
            passed=True,
            message="Цель сформулирована конкретно, без расплывчатых формулировок"
        ))

    # 2. Измеримость (Measurable)
    has_numbers = bool(re.search(r'\d', goal))
    has_measure = any(m in combined_text for m in MEASURE_INDICATORS)

    if not has_numbers and not has_measure:
        checks.append(ValidationCheck(
            name="Измеримость (Measurable)",
            passed=False,
            message="Отсутствуют числовые метрики и единицы измерения"
        ))
        score -= 20
        suggestions.append(
            "Добавьте количественные показатели: проценты, суммы, количество единиц, сроки."
        )
    elif not has_numbers:
        checks.append(ValidationCheck(
            name="Измеримость (Measurable)",
            passed=False,
            message="Единицы измерения есть, но отсутствуют конкретные числа"
        ))
        score -= 10
        suggestions.append("Укажите конкретные числовые значения целей.")
    else:
        checks.append(ValidationCheck(
            name="Измеримость (Measurable)",
            passed=True,
            message="Присутствуют числовые метрики или единицы измерения"
        ))

    # 3. Достижимость (Achievable)
    # Проверяем, не слишком ли амбициозна цель (очень большие числа без контекста)
    numbers = re.findall(r'\d+(?:[.,]\d+)?', goal)
    if numbers:
        max_num = max([float(n.replace(',', '.')) for n in numbers])
        # Эвристика: если число > 1000 без контекста, возможно это не конкретная метрика
        if max_num > 1000 and 'руб' not in goal_lower and 'usd' not in goal_lower:
            checks.append(ValidationCheck(
                name="Достижимость (Achievable)",
                passed=False,
                message=f"Целевое значение {max_num} выглядит чрезмерно амбициозным без контекста"
            ))
            score -= 10
            suggestions.append("Убедитесь, что целевое значение реалистично для текущих ресурсов.")
        else:
            checks.append(ValidationCheck(
                name="Достижимость (Achievable)",
                passed=True,
                message="Цель выглядит достижимой с учётом ресурсов"
            ))
    else:
        checks.append(ValidationCheck(
            name="Достижимость (Achievable)",
            passed=True,
            message="Требуется уточнение для оценки достижимости"
        ))

    # 4. Актуальность (Relevant)
    corporate_keywords = ["норникель", "дивиденд", "ebitda", "fcf", "мсфо", "производств", "цифровизац"]
    has_corporate_link = any(kw in combined_text for kw in corporate_keywords)

    if has_corporate_link:
        checks.append(ValidationCheck(
            name="Актуальность (Relevant)",
            passed=True,
            message="Цель связана с корпоративными приоритетами"
        ))
    else:
        checks.append(ValidationCheck(
            name="Актуальность (Relevant)",
            passed=True,
            message="Проверьте связь цели со стратегией компании"
        ))

    # 5. Ограниченность по времени (Time-bound)
    has_time = any(t in combined_text for t in TIME_MARKERS)
    if not has_time:
        checks.append(ValidationCheck(
            name="Ограниченность по времени (Time-bound)",
            passed=False,
            message="Не указан срок достижения цели"
        ))
        score -= 15
        suggestions.append(
            "Укажите чёткий дедлайн: 'до конца Q3 2025', 'в течение 6 месяцев', 'к 31.12.2025'."
        )
    else:
        checks.append(ValidationCheck(
            name="Ограниченность по времени (Time-bound)",
            passed=True,
            message="Срок достижения указан"
        ))

    # 6. Key Results
    kr_count = len([kr for kr in key_results if kr.strip()])
    if kr_count < 2:
        checks.append(ValidationCheck(
            name="Key Results",
            passed=False,
            message=f"Добавьте минимум 2-3 ключевых результата (сейчас {kr_count})"
        ))
        score -= 15
        suggestions.append("Рекомендуется определить 2-5 конкретных Key Results для измерения прогресса.")
    elif kr_count > 5:
        checks.append(ValidationCheck(
            name="Key Results",
            passed=False,
            message=f"Слишком много Key Results ({kr_count}), рекомендуется 2-5"
        ))
        score -= 5
        suggestions.append("Сократите количество Key Results до 5, чтобы сохранить фокус.")
    else:
        checks.append(ValidationCheck(
            name="Key Results",
            passed=True,
            message=f"Оптимальное количество Key Results: {kr_count}"
        ))

    score = max(0, min(100, score))
    is_valid = score >= 70

    return ValidationResult(
        is_valid=is_valid,
        score=score,
        checks=checks,
        suggestions=suggestions
    )
