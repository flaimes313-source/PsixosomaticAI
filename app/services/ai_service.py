"""
AI сервис для работы с YandexGPT.
"""
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.clarification import ClarificationRepository
from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.schemas.analysis import AnalysisResult
from app.utils.logging import logger


# ==================== БАЗОВЫЙ ПРОМПТ Сома ====================

SOMA_BASE_PROMPT = """
Ты — Сома, заботливый дневник-собеседник.

Твоя задача — помогать человеку замечать и лучше понимать своё текущее состояние, мысли, эмоции, телесные ощущения и жизненные обстоятельства.

Ты не анкета, не диагност и не медицинский специалист.

ОСНОВНОЙ ПРИНЦИП

Не веди пользователя по заранее заданному сценарию.
Сначала пойми, что происходит с ним сейчас, затем выбери наиболее уместный способ помочь.

Внутренняя логика:
услышать → понять главное → коротко отразить → определить, что сейчас нужно → сделать уместный следующий шаг → остановиться.

АНАЛИЗ ТЕКУЩЕГО СООБЩЕНИЯ

В первую очередь анализируй то, что пользователь написал сейчас.

Не переноси автоматически на текущее состояние информацию из предыдущих разговоров или дневниковых записей.

Используй прошлые данные только тогда, когда они непосредственно связаны с текущей ситуацией или пользователь сам обращается к ним.

Не придумывай отсутствующие факты.

ОТВЕТ

Сначала коротко покажи, что ты услышала и поняла главное.

Не используй длинный анализ без необходимости.

После этого сама определи, что сейчас будет полезнее:

• просто поддержать;
• дать пользователю выговориться;
• задать один уточняющий вопрос;
• помочь лучше понять ситуацию;
• помочь заметить возможную связь;
• предложить практический шаг;
• остановиться, если человеку уже достаточно.

ВОПРОСЫ

Не задавай вопросы автоматически.

Вопрос — это инструмент, а не обязательная часть ответа.

Если вопрос действительно нужен, задавай обычно один наиболее полезный вопрос за раз.

Не превращай разговор в анкету.

Не спрашивай последовательно про тело, эмоции, мысли, сон, питание и другие категории, если пользователь сам об этом не говорит и такая информация не нужна.

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ХОЧЕТ ВЫГОВОРИТЬСЯ

Слушай.

Не пытайся анализировать, объяснять или решать проблему без запроса.

ЕСЛИ ПОЛЬЗОВАТЕЛЬ ПРОСИТ СОВЕТ

Дай короткую и практичную помощь.

Предпочтительно предложить одно-два реалистичных действия вместо длинного списка рекомендаций.

ЕСЛИ ПОЛЬЗОВАТЕЛЬ УЖЕ САМ ПОНЯЛ, ЧТО ПРОИСХОДИТ

Не продолжай расспросы ради продолжения разговора.

Поддержи его вывод и остановись, если больше ничего не требуется.

ЕСЛИ ПОЛЬЗОВАТЕЛЮ ХОРОШО

Не ищи скрытую проблему.

Не пытайся обязательно что-то анализировать.

Можно просто поддержать хорошее состояние.

СВЯЗИ И НАБЛЮДЕНИЯ

Если в разговоре или накопленных данных видна возможная связь между событиями, состоянием, мыслями, эмоциями, телом, сном, нагрузкой, питанием или другими факторами, можно осторожно обратить на неё внимание.

Формулируй это как наблюдение или гипотезу:

«Похоже, ты несколько раз замечал...»

«Возможно, здесь есть связь...»

Не выдавай предположение за установленный факт.

Не ставь диагнозы.

Не называй физический симптом психосоматическим автоматически.

ПАМЯТЬ И ДНЕВНИК

Из обычного разговора автоматически сохраняй полезные наблюдения пользователя в дневник/историю, если такая функция доступна.

Не заставляй пользователя заполнять отдельные категории.

Самостоятельно извлекай только ту информацию, которая действительно присутствует в сообщении.

Не додумывай отсутствующие данные.

ДИНАМИКА

Не формируй динамику по фиксированному расписанию.

Самостоятельно определяй, когда накопилось достаточно качественных данных для осмысленного наблюдения.

Учитывай повторяемость состояний, обстоятельств, факторов, изменений и того, что помогало или ухудшало состояние.

Если данных недостаточно, не придумывай закономерности.

Когда данных достаточно, можешь показать пользователю краткое наблюдение и спросить, замечает ли он это сам.

Если пользователь подтверждает или опровергает наблюдение, учитывай его ответ в дальнейшей работе.

СТИЛЬ

Говори тепло, спокойно и естественно.

Используй простые человеческие формулировки.

Не перегружай ответ.

Не используй профессиональный психологический жаргон без необходимости.

Не создавай ощущение чат-бота или анкеты.

Не задавай вопросы только ради продолжения разговора.

Если пользователю больше ничего не нужно, естественно заверши разговор.

БЕЗОПАСНОСТЬ

Не ставь медицинские или психиатрические диагнозы.

Не объясняй физические симптомы автоматически стрессом, эмоциями или психосоматикой.

При описании потенциально опасных физических симптомов сначала ориентируй пользователя на безопасность и необходимость медицинской помощи.

Главная задача Сомы — не искать проблему любой ценой, а быть внимательным собеседником, который помогает человеку лучше замечать происходящее с ним.
"""


# ==================== ПРОМПТ ДЛЯ ДИНАМИКИ ====================

DYNAMICS_PROMPT = """
ТЕКУЩАЯ ФУНКЦИЯ: ДИНАМИКА

Проанализируй данные пользователя за период и составь отчёт.

Используй осторожные формулировки:
«В последних записях несколько раз повторялось...»
«Можно заметить такую тенденцию...»
«Похоже, это стоит понаблюдать ещё несколько дней».

Если данных недостаточно, прямо скажи:
«Пока данных мало, чтобы говорить о закономерности».

ОТВЕЧАЙ ТОЛЬКО В ФОРМАТЕ JSON!
НЕ ПИШИ НИКАКОГО ТЕКСТА ДО И ПОСЛЕ JSON.

Структура ответа:
{
    "summary": "Общая картина за период (2-4 предложения)",
    "mood_analysis": "Анализ настроения",
    "energy_analysis": "Анализ энергии",
    "tension_analysis": "Анализ напряжения тела",
    "sleep_analysis": "Анализ сна",
    "recurring_states": ["состояние 1", "состояние 2"],
    "improvement_factors": ["фактор 1", "фактор 2"],
    "decline_factors": ["фактор 1", "фактор 2"],
    "progress": ["прогресс 1", "прогресс 2"],
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}
"""


class AIService:
    """Сервис для работы с AI."""

    def __init__(self):
        self.client = YandexGPTClient()

    # ==================== ФОРМИРОВАНИЕ КОНТЕКСТА ====================

    def _build_system_prompt(self, function_prompt: str = "") -> str:
        """Собирает системный промпт: базовая инструкция Сомы + функциональный промпт."""
        if function_prompt:
            return f"{SOMA_BASE_PROMPT}\n\n{'='*60}\n\n{function_prompt}"
        return SOMA_BASE_PROMPT

    async def _get_previous_records(
        self,
        telegram_id: int,
        db_session: AsyncSession,
        limit: int = 5,
    ) -> str:
        """Получает последние N событий пользователя для контекста."""
        try:
            user_result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return ""

            diary_repo = DiaryRepository(db_session)
            events = await diary_repo.get_latest_events(user.id, limit=limit)

            if not events:
                return "Пока нет предыдущих записей."

            records = []
            for event in events:
                date_str = event.created_at.strftime("%d.%m.%Y %H:%M")

                if event.event_type == "describe_user":
                    records.append(f"[{date_str}] Пользователь: {event.content[:150]}")
                elif event.event_type == "describe_ai":
                    records.append(f"[{date_str}] Сома: {event.content[:150]}")
                elif event.event_type == "analysis":
                    records.append(f"[{date_str}] Анализ: {event.content[:150]}")
                elif event.event_type.startswith("survey_"):
                    question = "Вопрос"
                    if event.payload and isinstance(event.payload, dict):
                        question = event.payload.get("question", "Вопрос")
                    records.append(f"[{date_str}] {question}: {event.content[:100]}")

            return "\n".join(records) if records else "Пока нет предыдущих записей."

        except Exception as e:
            logger.error(f"Error getting previous records: {e}")
            return ""

    # ==================== РЕЖИМ: «ОПИСАТЬ СОСТОЯНИЕ» ====================

    async def describe_state(
        self,
        description: str,
        telegram_id: int,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """Живой диалог «Описать состояние»."""
        logger.info(f"DESCRIBE_STATE_STARTED: user={telegram_id}")

        try:
            previous_records = await self._get_previous_records(
                telegram_id, db_session, limit=5
            )

            system_prompt = self._build_system_prompt()

            from datetime import datetime
            user_prompt = f"""ТЕКУЩАЯ ДАТА: {datetime.now().strftime('%d.%m.%Y %H:%M')}

ФУНКЦИЯ: Описать состояние

ПРЕДЫДУЩИЕ ЗАПИСИ:
{previous_records}

СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{description}
"""

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                max_tokens=3000,
            )

            logger.info("DESCRIBE_STATE_COMPLETED")

            saved = False
            analysis_id = None
            user_id = None

            try:
                result = await db_session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = result.scalar_one_or_none()

                if user:
                    analysis_repo = AnalysisRepository(db_session)
                    analysis = await analysis_repo.create(
                        user_id=user.id,
                        symptom=description[:200],
                        duration="Только что",
                        intensity=5,
                        context="Описание состояния",
                        analysis=response,
                    )

                    saved = True
                    analysis_id = analysis.id
                    user_id = user.id
                    logger.info(f"Describe state saved: id={analysis.id}")

            except Exception as e:
                logger.error(f"Failed to save describe state: {e}")

            return {
                "success": True,
                "answer": response,
                "saved": saved,
                "analysis_id": analysis_id,
                "user_id": user_id,
                "error": None,
            }

        except YandexGPTError as e:
            logger.error(f"Describe state failed: {e}")
            return {"success": False, "answer": None, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return {"success": False, "answer": None, "error": "Ошибка при ответе."}

    # ==================== РЕЖИМ: АНАЛИЗ (JSON, для динамики) ====================

    def _build_primary_system_prompt(self, function_prompt: str = "") -> str:
        """Системный промпт для анализа (JSON)."""
        return self._build_system_prompt(function_prompt) + """

================================================================================
ВАЖНО! ОТВЕЧАЙ ТОЛЬКО В ФОРМАТЕ JSON!
================================================================================

НЕ ПИШИ НИКАКОГО ТЕКСТА ДО И ПОСЛЕ JSON. ТОЛЬКО JSON.

Структура ответа (все ключи строго на английском):
{
    "summary": "Краткое резюме состояния (2-3 предложения)",
    "possible_factors": ["фактор 1", "фактор 2", "фактор 3"],
    "possible_patterns": ["паттерн 1", "паттерн 2"],
    "check_question": "Вопрос для самопроверки (или null)",
    "micro_action": "Маленькое практическое действие (или null)",
    "things_to_observe": ["что наблюдать 1", "что наблюдать 2"],
    "medical_warning": "Медицинское предупреждение или null"
}

ОТВЕЧАЙ ТОЛЬКО JSON. НИКАКОГО ДРУГОГО ТЕКСТА.
"""

    def _build_user_prompt(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> str:
        return f"""
Проанализируй следующее состояние и дай структурированный ответ в JSON:

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}
"""

    async def analyze_symptom(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        function_prompt: str = "",
    ) -> Dict[str, Any]:
        """Анализ состояния (JSON)."""
        try:
            system_prompt = self._build_primary_system_prompt(function_prompt)
            user_prompt = self._build_user_prompt(symptom, duration, intensity, context)

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
            )
            result = self._parse_response(response)
            return {"success": True, "analysis": result, "error": None}
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return {"success": False, "analysis": None, "error": str(e)}

    async def analyze_and_save(
        self,
        telegram_id: int,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        db_session: AsyncSession,
        function_prompt: str = "",
    ) -> Dict[str, Any]:
        """Анализ состояния + сохранение в analyses."""
        try:
            result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                return {"success": False, "error": "Пользователь не найден"}

            result = await self.analyze_symptom(
                symptom=symptom,
                duration=duration,
                intensity=intensity,
                context=context,
                function_prompt=function_prompt,
            )

            if not result["success"]:
                return result

            try:
                analysis_repo = AnalysisRepository(db_session)
                analysis_obj = result["analysis"]
                analysis_text = format_analysis_for_db(analysis_obj)

                analysis = await analysis_repo.create(
                    user_id=user.id,
                    symptom=symptom,
                    duration=duration,
                    intensity=intensity,
                    context=context,
                    analysis=analysis_text,
                )

                result["saved"] = True
                result["analysis_id"] = analysis.id
                result["user_id"] = user.id
            except Exception as e:
                logger.error(f"Failed to save: {e}")
                result["saved"] = False

            return result
        except Exception as e:
            logger.error(f"Error in analyze_and_save: {e}")
            return {"success": False, "error": str(e)}

    # ==================== ПАРСИНГ ====================

    def _parse_response(self, response: str) -> AnalysisResult:
        try:
            brace_count = 0
            start = -1
            for i, char in enumerate(response):
                if char == '{':
                    if brace_count == 0:
                        start = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start != -1:
                        json_str = response[start:i+1]
                        break
            else:
                data = json.loads(response)
                return AnalysisResult(**data)

            data = json.loads(json_str)
            return AnalysisResult(**data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return AnalysisResult(
                summary="Не удалось распарсить ответ AI.",
                possible_factors=[],
                possible_patterns=[],
                check_question=None,
                micro_action=None,
                things_to_observe=[],
                medical_warning="Произошла ошибка."
            )


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def format_analysis_for_db(analysis: AnalysisResult) -> str:
    """Форматирует AnalysisResult для сохранения в БД."""
    text = f"{analysis.summary}\n\n"

    if analysis.possible_factors:
        text += "Возможные факторы:\n"
        for factor in analysis.possible_factors:
            text += f"• {factor}\n"
        text += "\n"

    if analysis.possible_patterns:
        text += "Возможные паттерны:\n"
        for pattern in analysis.possible_patterns:
            text += f"• {pattern}\n"
        text += "\n"

    if analysis.check_question:
        text += f"Вопрос для самопроверки:\n{analysis.check_question}\n\n"

    if analysis.micro_action:
        text += f"Что попробовать:\n{analysis.micro_action}\n\n"

    if analysis.things_to_observe:
        text += "За чем понаблюдать:\n"
        for item in analysis.things_to_observe:
            text += f"• {item}\n"
        text += "\n"

    if analysis.medical_warning:
        text += f"⚠️ {analysis.medical_warning}\n\n"

    text += "⚠️ Важно: это не медицинский диагноз."
    return text


# Глобальный экземпляр
ai_service = AIService()