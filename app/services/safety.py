"""
Safety Engine — защитный слой для AI диалога.
Проверяет сообщения до и после YandexGPT.
"""
import re
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


class SafetyLevel(Enum):
    """Уровни безопасности."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class SafetyResult:
    """Результат проверки безопасности."""
    level: SafetyLevel
    is_safe: bool
    reason: Optional[str] = None
    warning: Optional[str] = None
    action: str = "continue"  # continue, continue_with_warning, stop_ai
    detected_patterns: List[str] = field(default_factory=list)


class SafetyService:
    """Сервис безопасности для AI диалога."""

    # ==================== CRITICAL ПАТТЕРНЫ ====================
    
    CRITICAL_PATTERNS = {
        # Сердечно-сосудистые
        "chest_pain": {
            "keywords": ["боль в груди", "давит в груди", "жжение в груди", "сжимает грудь", "сердце", "сердцебиение"],
            "context_words": ["сильная", "внезапная", "резкая", "невыносимая"],
            "warning": "⚠️ **Важно!**\n\nВы описали симптомы, которые могут требовать медицинского внимания. "
                       "Пожалуйста, обратитесь к врачу или вызовите скорую помощь при ухудшении состояния.\n\n"
                       "Психосоматический анализ не заменяет медицинскую диагностику."
        },
        "breathing": {
            "keywords": ["тяжело дышать", "не хватает воздуха", "одышка", "затрудненное дыхание", "задыхаюсь"],
            "context_words": ["внезапно", "резко", "сильно"],
            "warning": "⚠️ **Важно!**\n\nОдышка или затруднённое дыхание могут быть признаком серьёзного состояния. "
                       "Рекомендуется обратиться к врачу.\n\n"
                       "Это не медицинский диагноз, а рекомендация проверить своё здоровье."
        },
        # Неврологические
        "neurological": {
            "keywords": ["онемела", "онемение", "слабость в руке", "слабость в ноге", "асимметрия лица", "перекосило лицо"],
            "context_words": ["внезапно", "резко", "неожиданно"],
            "warning": "⚠️ **Важно!**\n\nВнезапная слабость или онемение могут быть признаками неврологического состояния. "
                       "Рекомендуется как можно скорее обратиться к врачу."
        },
        "consciousness": {
            "keywords": ["потеря сознания", "обморок", "отключился", "темнеет в глазах", "головокружение", "кружится голова"],
            "context_words": ["потерял", "упал", "отключился"],
            "warning": "⚠️ **Важно!**\n\nПотеря сознания или сильное головокружение — повод обратиться к врачу. "
                       "Пожалуйста, не откладывайте визит к специалисту."
        },
        "bleeding": {
            "keywords": ["кровотечение", "кровь", "сильное кровотечение", "обильное кровотечение"],
            "context_words": ["сильное", "обильное", "не останавливается"],
            "warning": "⚠️ **Важно!**\n\nПри сильном кровотечении необходимо срочно обратиться за медицинской помощью."
        },
        # Психологический кризис
        "suicide": {
            "keywords": ["самоубийство", "убить себя", "покончить с собой", "не хочу жить", "свести счёты"],
            "context_words": ["хочу", "думаю", "планирую", "собираюсь"],
            "warning": "⚠️ **Важно!**\n\nВы не один. Пожалуйста, обратитесь за помощью:\n\n"
                       "☎️ Телефон доверия: 8-800-2000-122\n"
                       "☎️ Психологическая помощь: 112\n\n"
                       "Ваша жизнь важна. Пожалуйста, не оставайтесь с этим один на один."
        },
        "self_harm": {
            "keywords": ["порезать себя", "навредить себе", "причинить себе боль", "резать вены"],
            "context_words": ["хочу", "буду", "собираюсь"],
            "warning": "⚠️ **Важно!**\n\nВы не один. Пожалуйста, обратитесь за помощью:\n\n"
                       "☎️ Телефон доверия: 8-800-2000-122\n"
                       "☎️ Психологическая помощь: 112\n\n"
                       "Ваша жизнь важна. Не оставайтесь с этим один на один."
        },
        "severe_pain": {
            "keywords": ["невыносимая боль", "адская боль", "терпеть невозможно", "сильнейшая боль"],
            "context_words": ["внезапно", "резко", "невыносимо"],
            "warning": "⚠️ **Важно!**\n\nСильная боль, особенно внезапная, может требовать медицинского внимания. "
                       "Рекомендуется обратиться к врачу."
        },
    }

    # ==================== WARNING ПАТТЕРНЫ ====================

    WARNING_PATTERNS = {
        "persistent_symptom": {
            "keywords": ["уже неделю", "второй месяц", "давно", "постоянно", "каждый день", "уже давно"],
            "warning": "⚠️ Длительные симптомы рекомендуется проверить у врача. "
                       "Этот анализ не заменяет медицинскую консультацию."
        },
        "worsening": {
            "keywords": ["усиливается", "становится хуже", "сильнее", "прогрессирует", "нарастает"],
            "warning": "⚠️ Если симптомы усиливаются или не проходят, рекомендуется обратиться к врачу."
        },
        "fever": {
            "keywords": ["температура", "жар", "лихорадка", "озноб"],
            "warning": "⚠️ Повышенная температура — повод обратиться к врачу. "
                       "Не пытайтесь лечиться самостоятельно без консультации."
        },
        "sleep_disturbance": {
            "keywords": ["бессонница", "не сплю", "плохо сплю", "просыпаюсь ночью", "трудно заснуть"],
            "context_words": ["неделя", "месяц", "давно", "постоянно"],
            "warning": "⚠️ Длительная бессонница может влиять на здоровье. "
                       "Рекомендуется обсудить это с врачом."
        },
        "weight_loss": {
            "keywords": ["потеря веса", "худею", "вес падает", "похудела", "похудел"],
            "warning": "⚠️ Необъяснимая потеря веса — повод обратиться к врачу."
        },
    }

    # ==================== ПРОВЕРКА ДО AI ====================

    def check_input(self, text: str) -> SafetyResult:
        """
        Проверяет сообщение пользователя перед отправкой в AI.
        """
        if not text or len(text.strip()) < 3:
            return SafetyResult(
                level=SafetyLevel.NORMAL,
                is_safe=True,
                action="continue"
            )

        # Проверяем CRITICAL паттерны
        for pattern_key, pattern_data in self.CRITICAL_PATTERNS.items():
            result = self._check_critical(text, pattern_key, pattern_data)
            if result:
                return result

        # Проверяем WARNING паттерны
        for pattern_key, pattern_data in self.WARNING_PATTERNS.items():
            result = self._check_warning(text, pattern_key, pattern_data)
            if result:
                return result

        return SafetyResult(
            level=SafetyLevel.NORMAL,
            is_safe=True,
            action="continue"
        )

    def check_context(self, symptom: str, duration: str, intensity: int, context: str) -> SafetyResult:
        """
        Проверяет полный контекст (симптом + длительность + интенсивность + контекст).
        """
        # Собираем весь текст для проверки
        full_text = f"{symptom} {duration} {context} {intensity}"
        
        # Проверяем интенсивность
        if intensity >= 8:
            intensity_warning = "⚠️ Вы оценили интенсивность симптома как 8-10 из 10. "
            intensity_warning += "Сильная боль или дискомфорт могут требовать медицинского внимания."
            
            # Проверяем, не является ли это CRITICAL
            critical_result = self.check_input(f"{full_text} сильная боль интенсивность {intensity}")
            if critical_result.level == SafetyLevel.CRITICAL:
                return critical_result
            
            return SafetyResult(
                level=SafetyLevel.WARNING,
                is_safe=True,
                reason="high_intensity",
                warning=intensity_warning,
                action="continue_with_warning"
            )

        # Проверяем полный текст через check_input
        return self.check_input(full_text)

    # ==================== ПРОВЕРКА ПОСЛЕ AI ====================

    def check_output(self, text: str) -> SafetyResult:
        """
        Проверяет ответ YandexGPT перед отправкой пользователю.
        """
        if not text:
            return SafetyResult(
                level=SafetyLevel.NORMAL,
                is_safe=True,
                action="continue"
            )

        # Запрещённые категоричные утверждения
        categorical_phrases = [
            "точно вызван", "определённо связано", "несомненно", "абсолютно уверен",
            "точно психосоматика", "без сомнения", "это точно", "я уверен",
            "ваша проблема", "вы сами создали", "вы подавляете", "ваше тело кричит"
        ]

        for phrase in categorical_phrases:
            if phrase.lower() in text.lower():
                return SafetyResult(
                    level=SafetyLevel.WARNING,
                    is_safe=True,
                    reason="categorical_statement",
                    warning="⚠️ Помните: это предположительный анализ, а не медицинский диагноз. "
                            "Причины симптомов могут быть разными.",
                    action="continue_with_warning"
                )

        # Опасные медицинские утверждения
        medical_assertions = [
            "вам не нужно обращаться к врачу", "не обращайтесь к врачу",
            "отменяйте лекарства", "прекратите принимать", "не принимайте лекарства",
            "у вас депрессия", "у вас тревожное расстройство", "у вас паническое расстройство",
            "у вас гастрит", "у вас язва", "у вас астма", "у вас диабет",
            "я диагностирую", "я ставлю диагноз", "ваш диагноз"
        ]

        for phrase in medical_assertions:
            if phrase.lower() in text.lower():
                return SafetyResult(
                    level=SafetyLevel.CRITICAL,
                    is_safe=False,
                    reason="dangerous_medical_assertion",
                    warning="⚠️ Бот не ставит медицинские диагнозы и не даёт медицинских рекомендаций. "
                            "Пожалуйста, обратитесь к врачу для профессиональной консультации.",
                    action="stop_ai"
                )

        return SafetyResult(
            level=SafetyLevel.NORMAL,
            is_safe=True,
            action="continue"
        )

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def _check_critical(self, text: str, pattern_key: str, pattern_data: dict) -> Optional[SafetyResult]:
        """
        Проверяет наличие критических паттернов в тексте.
        """
        text_lower = text.lower()
        keywords = pattern_data.get("keywords", [])
        context_words = pattern_data.get("context_words", [])

        # Проверяем наличие ключевых слов
        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        if not found_keywords:
            return None

        # Проверяем наличие контекстных слов (усилителей)
        found_context = []
        for context_word in context_words:
            if context_word.lower() in text_lower:
                found_context.append(context_word)

        # Если есть ключевое слово, проверяем серьёзность
        if found_keywords:
            # Если есть хотя бы одно контекстное слово - CRITICAL
            if found_context:
                return SafetyResult(
                    level=SafetyLevel.CRITICAL,
                    is_safe=False,
                    reason=pattern_key,
                    warning=pattern_data.get("warning", ""),
                    action="stop_ai",
                    detected_patterns=found_keywords + found_context
                )
            
            # Если нет контекстных слов, но есть ключевое - WARNING
            return SafetyResult(
                level=SafetyLevel.WARNING,
                is_safe=True,
                reason=pattern_key,
                warning="⚠️ В вашем сообщении упоминаются симптомы, которые могут требовать внимания. "
                        "Рекомендуется проконсультироваться с врачом для исключения серьёзных причин.",
                action="continue_with_warning",
                detected_patterns=found_keywords
            )

        return None

    def _check_warning(self, text: str, pattern_key: str, pattern_data: dict) -> Optional[SafetyResult]:
        """
        Проверяет наличие предупреждающих паттернов в тексте.
        """
        text_lower = text.lower()
        keywords = pattern_data.get("keywords", [])
        context_words = pattern_data.get("context_words", [])

        found_keywords = []
        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        if not found_keywords:
            return None

        # Если есть контекстные слова, проверяем
        if context_words:
            for context_word in context_words:
                if context_word.lower() in text_lower:
                    return SafetyResult(
                        level=SafetyLevel.WARNING,
                        is_safe=True,
                        reason=pattern_key,
                        warning=pattern_data.get("warning", ""),
                        action="continue_with_warning",
                        detected_patterns=found_keywords
                    )
        else:
            # Без контекстных слов просто предупреждение
            return SafetyResult(
                level=SafetyLevel.WARNING,
                is_safe=True,
                reason=pattern_key,
                warning=pattern_data.get("warning", ""),
                action="continue_with_warning",
                detected_patterns=found_keywords
            )

        return None

    def format_warning_for_telegram(self, result: SafetyResult, original_text: str) -> str:
        """
        Форматирует предупреждение для отправки в Telegram.
        """
        if result.level == SafetyLevel.NORMAL:
            return original_text

        if result.level == SafetyLevel.CRITICAL:
            return result.warning or "⚠️ Обратитесь к врачу."

        if result.level == SafetyLevel.WARNING:
            # Добавляем предупреждение к оригинальному тексту
            warning_text = f"\n\n---\n\n{result.warning}\n\n⚠️ Это не медицинский диагноз."
            if result.action == "continue_with_warning":
                return f"{original_text}{warning_text}"

        return original_text


# Создаём глобальный экземпляр
safety_service = SafetyService()