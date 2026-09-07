"""
Список аффирмаций для утреннего опроса с чередованием.
"""
from typing import List

AFFIRMATIONS: List[str] = [
    "Моё тело — мой союзник. Я учусь слышать его сигналы.",
    "Сегодня я могу заметить больше, чем вчера.",
    "Я разрешаю себе чувствовать и быть в контакте с собой.",
    "Утро задаёт тон дню. Как ты начнёшь его?",
]

_affirmation_index: int = 0


def get_next_affirmation() -> str:
    """Возвращает следующую аффирмацию по очереди."""
    global _affirmation_index
    aff = AFFIRMATIONS[_affirmation_index % len(AFFIRMATIONS)]
    _affirmation_index += 1
    return aff


def reset_affirmation_index() -> None:
    """Сбрасывает индекс аффирмаций (для тестов)."""
    global _affirmation_index
    _affirmation_index = 0