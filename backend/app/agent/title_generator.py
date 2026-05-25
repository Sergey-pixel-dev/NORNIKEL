"""
Генерация заголовка цели на основе описания.
Сейчас rule-based, placeholder для Qwen.
"""

import re


DOMAIN_KEYWORDS = {
    "цифровизац": "Цифровизация",
    "производств": "Производство",
    "финанс": "Финансы",
    "безопасност": "Безопасность",
    "эколог": "Экология",
    "кадр": "Кадры",
    "продаж": "Продажи",
    "логистик": "Логистика",
    "it": "IT",
    "автоматизац": "Автоматизация",
}


def generate_title(description: str) -> str:
    """Генерирует заголовок цели из описания."""
    if not description:
        return "Новая цель"

    desc_lower = description.lower()

    # 1. Определяем домен
    domain = "Цель"
    for keyword, domain_name in DOMAIN_KEYWORDS.items():
        if keyword in desc_lower:
            domain = domain_name
            break

    # 2. Извлекаем ключевые слова (существительные и глаголы)
    # Убираем стоп-слова
    stop_words = {
        "и", "в", "на", "с", "по", "для", "до", "от", "из", "за", "под", "над",
        "при", "про", "без", "через", "после", "перед", "между", "об", "по",
        "не", "но", "а", "или", "что", "как", "который", "этот", "такой",
        "все", "его", "ее", "их", "мы", "вы", "они", "он", "она", "оно",
        "год", "2025", "2026", "2027", "q1", "q2", "q3", "q4", "процент",
        "млн", "тыс", "руб", "usd", "по", "от", "до", "на",
    }

    # Чистим текст
    cleaned = re.sub(r'[^\w\s]', ' ', desc_lower)
    words = [w.strip() for w in cleaned.split() if len(w.strip()) > 3]
    filtered = [w for w in words if w not in stop_words][:4]

    if filtered:
        action = " ".join(filtered)
        # Капитализируем первую букву
        action = action.capitalize()
    else:
        action = domain

    # 3. Добавляем метрику если есть
    metric = ""
    numbers = re.findall(r'\d+(?:[.,]\d+)?\s*(?:%|процент|руб|usd|млн|тыс|дней|месяц)', desc_lower)
    if numbers:
        metric = f" ({numbers[0].strip()})"

    title = f"{domain}: {action}{metric}"
    # Обрезаем до 100 символов
    if len(title) > 100:
        title = title[:97] + "..."

    return title
