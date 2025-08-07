"""Помощник для перевода комментариев и строк на русский язык."""

# Словарь основных переводов для проекта
TRANSLATIONS = {
    # Общие термины
    "Processing": "Обработка",
    "Document": "Документ", 
    "Workflow": "Рабочий процесс",
    "Model": "Модель",
    "Retry": "Повтор",
    "Fallback": "Отказоустойчивость",
    "Circuit breaker": "Автоматический выключатель",
    "Quality check": "Проверка качества",
    "Human review": "Ручное рассмотрение",
    "Decision": "Решение",
    "Risk assessment": "Оценка риска",
    "Loan application": "Кредитная заявка",
    
    # Статусы
    "completed": "завершено",
    "failed": "неудача",
    "pending": "ожидание",
    "approved": "одобрено", 
    "declined": "отклонено",
    "requires manual review": "требует ручного рассмотрения",
    
    # Сообщения об ошибках
    "Classification failed": "Классификация не удалась",
    "Processing failed": "Обработка не удалась", 
    "Validation failed": "Валидация не удалась",
    "All models failed": "Все модели не смогли",
    "Circuit breaker opened": "Circuit breaker открыт",
    
    # Логирование
    "INFO": "ИНФО",
    "WARNING": "ПРЕДУПРЕЖДЕНИЕ", 
    "ERROR": "ОШИБКА",
    "DEBUG": "ОТЛАДКА",
    
    # Типы файлов
    "invoice": "счет",
    "contract": "контракт",
    "receipt": "квитанция",
    "pay_stub": "справка о зарплате",
    "bank_statement": "банковская выписка",
    "credit_report": "кредитный отчет",
}

def translate_text(text: str) -> str:
    """Переводит текст используя словарь переводов."""
    result = text
    for english, russian in TRANSLATIONS.items():
        result = result.replace(english, russian)
    return result

if __name__ == "__main__":
    print("Помощник перевода для проекта LangGraph Research")
    print("Основные переводы:")
    for en, ru in TRANSLATIONS.items():
        print(f"  {en} -> {ru}")