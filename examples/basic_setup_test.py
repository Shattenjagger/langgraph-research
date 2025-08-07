"""Basic test to verify local model setup works."""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую папку проекта в Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.local_model_manager import LocalModelManager
from src.models.model_configs import ModelType

logging.basicConfig(level=logging.INFO)


async def test_basic_model_setup():
    """Тест подключения и использования локальных моделей."""
    manager = LocalModelManager()
    
    # Проверяем какие модели доступны
    available = manager.get_available_models()
    print(f"Доступные модели: {[m.value for m in available]}")
    
    if not available:
        print("Модели недоступны. Убедитесь, что Ollama запущен и модели установлены.")
        return
    
    # Тестируем каждую доступную модель простым промптом
    test_prompt = "What is 2+2? Answer briefly."
    
    for model_type in available:
        print(f"\n--- Тестирование модели {model_type.value} ---")
        try:
            response = await manager.invoke_with_fallback(model_type, test_prompt)
            print(f"Ответ: {response}")
        except Exception as e:
            print(f"Ошибка: {e}")


async def test_fallback_mechanism():
    """Тест отказоустойчивости от сложных к простым моделям."""
    manager = LocalModelManager()
    
    # Создаем сценарий где модель рассуждений может не справиться/превысить время
    complex_prompt = """
    Analyze this complex business scenario and provide detailed recommendations:
    A company has declining sales but increasing customer satisfaction scores.
    Provide a 500-word analysis with specific action items.
    """
    
    print("\n--- Тестирование механизма отказоустойчивости ---")
    try:
        response = await manager.invoke_with_fallback(
            ModelType.REASONING, 
            complex_prompt,
            max_retries=1  # Малое количество повторов для быстрого переключения на fallback
        )
        print(f"Финальный ответ: {response[:200]}...")
    except Exception as e:
        print(f"Все модели не справились: {e}")


if __name__ == "__main__":
    print("Тестирование настройки локальных моделей...")
    print("Убедитесь, что Ollama запущен с этими установленными моделями:")
    print("- ollama pull llama3.2:1b")
    print("- ollama pull llama3.2:3b") 
    print("- ollama pull llama3.1:8b")
    print()
    
    asyncio.run(test_basic_model_setup())
    asyncio.run(test_fallback_mechanism())