#!/usr/bin/env python3
"""Утилита для запуска примеров проекта LangGraph Research."""

import sys
import subprocess
from pathlib import Path

def main():
    """Главная функция для запуска примеров."""
    if len(sys.argv) < 2:
        print("Использование: python run_example.py <номер_фазы>")
        print("Доступные фазы:")
        print("  basic - Базовая проверка настройки")
        print("  2 - Простая обработка документов")
        print("  3 - Условное ветвление")
        print("  4 - Механизмы повторных попыток") 
        print("  5 - Стратегии отказоустойчивости")
        print("  6 - Сложный рабочий процесс (ФИНАЛ)")
        return

    phase = sys.argv[1].lower()
    project_root = Path(__file__).parent
    
    example_files = {
        'basic': 'examples/basic_setup_test.py',
        '2': 'examples/phase2_document_processing.py',
        '3': 'examples/phase3_conditional_branching.py',
        '4': 'examples/phase4_retry_mechanisms.py',
        '5': 'examples/phase5_fallback_strategies.py',
        '6': 'examples/phase6_complex_workflow.py'
    }
    
    if phase not in example_files:
        print(f"Неизвестная фаза: {phase}")
        print("Доступные фазы:", ', '.join(example_files.keys()))
        return
    
    example_file = project_root / example_files[phase]
    
    if not example_file.exists():
        print(f"Файл не найден: {example_file}")
        return
    
    print(f"Запуск фазы {phase}...")
    print(f"Файл: {example_file}")
    print("-" * 50)
    
    try:
        # Запуск примера
        result = subprocess.run([sys.executable, str(example_file)], 
                              cwd=str(project_root),
                              check=True)
        print("-" * 50)
        print(f"Фаза {phase} завершена успешно!")
        
    except subprocess.CalledProcessError as e:
        print("-" * 50)
        print(f"Ошибка при выполнении фазы {phase}")
        print(f"Код ошибки: {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nВыполнение прервано пользователем")
        sys.exit(1)

if __name__ == "__main__":
    main()