"""
Простой тест подключения к YandexGPT.

Запускается отдельно от Telegram-бота.

Команда:

python test_yandex_gpt.py
"""

import asyncio

from app.services.yandex_gpt import (
    YandexGPTClient,
    YandexGPTError,
)


SYSTEM_PROMPT = """
Ты — тестовый AI-помощник.

Ответь кратко и понятно.

Не ставь медицинских диагнозов.
"""


USER_PROMPT = """
Привет!

Это тест подключения YandexGPT.

Ответь одной фразой:

«YandexGPT подключен успешно».
"""


async def main() -> None:
    """Запускает тестовый запрос."""

    try:
        client = YandexGPTClient()

        print("========================================")
        print("Тест подключения YandexGPT")
        print("========================================")
        print()

        print("Отправляю запрос...")

        response = await client.generate(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=USER_PROMPT,
        )

        print()
        print("Ответ YandexGPT:")
        print("----------------------------------------")
        print(response)
        print("----------------------------------------")
        print()
        print("✅ Подключение работает.")

    except YandexGPTError as exc:
        print()
        print("❌ Ошибка YandexGPT:")
        print(exc)

    except Exception as exc:
        print()
        print("❌ Неожиданная ошибка:")
        print(type(exc).__name__)
        print(exc)


if __name__ == "__main__":
    asyncio.run(main())