"""
Тест AI сервиса.

Запускается отдельно от Telegram-бота.

Команда:

python test_ai_service.py
"""

import asyncio

from app.services.ai_service import ai_service


async def main():
    """Тестирует AI сервис с реальными данными."""
    
    print("========================================")
    print("Тест AI сервиса")
    print("========================================")
    print()
    
    # Тестовые данные
    symptom = "Болит голова, особенно вечером"
    duration = "Несколько дней"
    intensity = 7
    context = "Усиливается при стрессе на работе"
    
    print("📋 Тестовые данные:")
    print(f"  Симптом: {symptom}")
    print(f"  Длительность: {duration}")
    print(f"  Интенсивность: {intensity}/10")
    print(f"  Контекст: {context}")
    print()
    
    print("🧠 Отправляю запрос в YandexGPT...")
    print()
    
    # Вызываем AI сервис
    result = await ai_service.analyze_symptom(
        symptom=symptom,
        duration=duration,
        intensity=intensity,
        context=context,
    )
    
    if result["success"]:
        print("✅ Анализ успешно получен!")
        print()
        print("Результат:")
        print("----------------------------------------")
        print(result["analysis"])
        print("----------------------------------------")
    else:
        print("❌ Ошибка:")
        print(result.get("error", "Неизвестная ошибка"))


if __name__ == "__main__":
    asyncio.run(main())