import re
from typing import List
from app.schemas import AIRewriteResponse


def mock_check_report(report_text: str, task_text: str) -> dict:
    score = 75 if len(report_text) > 100 else 45
    feedback = (
        "Отчет содержит основные пункты и соответствует задаче. Рекомендуется добавить количественные показатели."
        if score > 50
        else "Отчет слишком короткий или неполный. Требуется доработка с указанием конкретных результатов."
    )
    return {"score": score, "feedback": feedback}


VAGUE_WORDS = [
    "повысить", "улучшить", "оптимизировать", "эффективность", "качество",
    "стремиться", "пытаться", "понять", "изучить", "разобраться",
    "сделать лучше", "улучшить качество", "повысить уровень"
]


def ai_rewrite_goal(text: str) -> AIRewriteResponse:
    """
    Mock-реализация ИИ-рерайта цели.
    В будущем заменяется на вызов QWEN-27B в Yandex Cloud.
    """
    original = text.strip()
    lower = original.lower()

    # Простая эвристика: заменяем расплывчатые слова
    rewritten = original
    for word in VAGUE_WORDS:
        if word in lower:
            # Заменяем первое вхождение
            rewritten = re.sub(
                re.escape(word),
                "увеличить конкретный показатель на X%",
                rewritten,
                count=1,
                flags=re.IGNORECASE,
            )
            break

    # Добавляем SMART-форматирование если нет чисел
    if not re.search(r'\d', rewritten):
        rewritten += " (целевой показатель: +15% к текущему уровню, срок: до конца Q4 2026)"

    # Генерируем KR на основе ключевых слов
    key_results = _generate_krs(rewritten)

    return AIRewriteResponse(
        rewritten_goal=rewritten,
        key_results=key_results,
    )


def _generate_krs(goal: str) -> List[str]:
    """Генерирует 2–3 KR по ключевым словам цели."""
    krs = []
    lower = goal.lower()

    if any(w in lower for w in ["цифровизац", "автоматизац", "процесс"]):
        krs.append("Внедрить автоматизированный инструмент в 2 пилотных подразделениях")
        krs.append("Сократить время обработки заявки на 30%")
    elif any(w in lower for w in ["производств", "оборудован", "мониторинг"]):
        krs.append("Установить систему мониторинга на 100% целевого оборудования")
        krs.append("Снизить простои на 20% к концу года")
    elif any(w in lower for w in ["финанс", "отчётность", "бюджет"]):
        krs.append("Автоматизировать подготовку управленческой отчётности (ежемесячная)")
        krs.append("Сократить время закрытия месяца на 3 рабочих дня")
    else:
        krs.append("Достичь целевого показателя в пилотном проекте")
        krs.append("Подготовить методологию и обучить 10+ сотрудников")

    if len(krs) < 3:
        krs.append("Получить подтверждение эффекта от стейкхолдеров (NPS ≥ 8)")

    return krs
