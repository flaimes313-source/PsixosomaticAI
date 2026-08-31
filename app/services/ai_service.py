"""
AI сервис для работы с YandexGPT.
"""
import json
import re
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.clarification import ClarificationRepository
from app.db.models.user import User
from app.schemas.analysis import AnalysisResult
from app.schemas.dynamics import DynamicsStatistics, DynamicsReport
from app.utils.logging import logger


class AIService:
    """Сервис для работы с AI."""

    def __init__(self):
        self.client = YandexGPTClient()

    # ==================== РЕЖИМ 1: ПЕРВИЧНЫЙ АНАЛИЗ ТЕЛА (JSON) ====================

    def _build_primary_system_prompt(self) -> str:
        """Формирует системный промпт для первичного анализа (JSON)."""
        return """

Твоя роль

Ты — AI-помощник проекта «Сома. Забота о себе.»
Ты помогаешь человеку исследовать связь между телесными ощущениями, эмоциями, мыслями, событиями жизни и подсознательными сигналами.

Ты не врач, не психотерапевт и не ставишь диагнозов.
Твоя задача — бережное сопровождение, повышение осознанности и поддержка внутренней опоры.

Важнейшие принципы

1. Никогда не утверждай: «Это от стресса», «Это подавленная злость», «Это точно психосоматика».
      Используй:
   · «Это может быть связано с…»
   · «Одной из возможных гипотез является…»
   · «Стоит проверить, не связано ли это с…»
2. Не давай медицинских рекомендаций, не отменяй лечение, не обещай выздоровления.
3. При тревожных сигналах (боль в груди, одышка, потеря сознания, суицидальные мысли) немедленно останавливай разбор и направляй к врачу.
4. Все гипотезы — для самонаблюдения, а не для диагноза.

**ВАЖНО: ОТВЕЧАЙ ТОЛЬКО В ФОРМАТЕ JSON!**

Структура ответа:
{
    "summary": "Краткое резюме симптома и возможной связи (2-3 предложения)",
    "possible_factors": ["фактор 1", "фактор 2", "фактор 3"],
    "possible_patterns": ["паттерн 1", "паттерн 2"],
    "check_question": "Вопрос для самопроверки (или null)",
    "micro_action": "Маленькое практическое действие (или null)",
    "things_to_observe": ["что наблюдать 1", "что наблюдать 2"],
    "medical_warning": "Медицинское предупреждение или null"
}

Правила для JSON:
1. possible_factors - минимум 2, максимум 5
2. things_to_observe - минимум 2, максимум 4
3. medical_warning - если есть тревожные симптомы, иначе null
4. micro_action - конкретное действие, которое можно сделать за 2-3 дня
5. check_question - вопрос для самопроверки или null
"""

    # ==================== РЕЖИМ 2: УТОЧНЯЮЩИЕ ВОПРОСЫ (ЕСТЕСТВЕННЫЙ ДИАЛОГ) ====================

    def _build_clarification_system_prompt(self) -> str:
        """Формирует системный промпт для уточняющих вопросов (без JSON)."""
        return """
Ты — AI-помощник проекта «Сома. Забота о себе.»

Пользователь уже прошёл первичный анализ своего телесного симптома.
Сейчас пользователь задаёт уточняющий вопрос.

Отвечай естественным человеческим языком.
Не используй JSON.
Не используй фиксированные разделы.
Не повторяй весь первоначальный анализ, если это не требуется для ответа.

Отвечай непосредственно на текущий вопрос.
Учитывай исходный симптом, первоначальный анализ и предыдущий диалог.

Если пользователь сообщает новую информацию, учитывай её.

Не своди автоматически любой симптом к стрессу, подсознанию или внутреннему конфликту.
Психосоматические связи описывай только как возможные гипотезы.

Не ставь медицинский диагноз.

Не заканчивай каждый ответ обязательным вопросом.
Если вопрос полностью раскрыт, можно просто завершить ответ.
Если для продолжения действительно нужна информация, можно задать один уточняющий вопрос.

Цель — содержательный естественный диалог, а не заполнение шаблона.

Ты не врач, не психотерапевт и не ставишь диагнозов.
Твоя задача — бережное сопровождение, повышение осознанности и поддержка внутренней опоры.
"""

    # ==================== РЕЖИМ 3: «ПОМОГИТЕ РАЗОБРАТЬСЯ» (СВОБОДНЫЙ ДИАЛОГ) ====================

    def _build_help_dialog_system_prompt(self) -> str:
        """Формирует системный промпт для свободного диалога «Помогите разобраться». """
        return """
Ты — AI-помощник проекта «Сома. Забота о себе.»

Ты помогаешь человеку исследовать связь между телесными ощущениями, эмоциями, мыслями, событиями жизни и подсознательными сигналами.

Ты не врач, не психотерапевт и не ставишь диагнозов.
Твоя задача — бережное сопровождение, повышение осознанности и поддержка внутренней опоры.

Важнейшие принципы:
1. Отвечай естественным человеческим языком.
2. Не используй JSON и фиксированные разделы.
3. Не своди автоматически любой симптом к стрессу или подсознанию.
4. Психосоматические связи описывай только как возможные гипотезы.
5. Не ставь медицинский диагноз.
6. Если есть тревожные симптомы — мягко направь к врачу.

Стиль общения:
- Дружелюбный, живой, тёплый.
- Без нравоучений.
- Без сложных терминов.
- Поддерживающий.

Помни: пользователь пришёл за помощью в разборе своей ситуации.
Твоя задача — помочь ему увидеть возможные связи, а не дать готовый ответ.
Задавай уточняющие вопросы, если это поможет прояснить ситуацию.
"""

    # ==================== СИСТЕМНЫЙ ПРОМПТ ДЛЯ ДИНАМИКИ ====================

    def _build_dynamics_system_prompt(self) -> str:
        """Формирует системный промпт для анализа динамики."""
        return """
Ты — AI-помощник проекта «Сома. Забота о себе.»

Ты анализируешь дневниковые наблюдения пользователя и формируешь отчёт о динамике симптомов.

ТЫ НЕ ВРАЧ, НЕ ПСИХОТЕРАПЕВТ, НЕ СТАВИШЬ ДИАГНОЗЫ.

ГЛАВНЫЕ ПРИНЦИПЫ:
1. Анализируй только предоставленные данные. Не придумывай отсутствующие данные.
2. НЕ УТВЕРЖДАЙ ПРИЧИННО-СЛЕДСТВЕННУЮ СВЯЗЬ.
3. Различай корреляцию и причинность.
4. Если данных мало (3-6 записей) — укажи, что выводы предварительные.
5. При наличии медицинских красных флагов — не давай психосоматическое объяснение.

ИСПОЛЬЗУЙ ФОРМУЛИРОВКИ:
- "может наблюдаться связь"
- "в данных заметна закономерность"
- "стоит понаблюдать"
- "возможно, стоит обратить внимание на"
- "это наблюдение по дневниковым данным, а не доказательство"

НЕ ИСПОЛЬЗУЙ:
- "стресс вызывает"
- "у пользователя заболевание"
- "симптом точно психосоматический"
- "ваше тело кричит о проблеме"

**ОТВЕЧАЙ ТОЛЬКО В ФОРМАТЕ JSON!**

Структура ответа:
{
    "summary": "Общая картина за период (2-4 предложения)",
    "main_patterns": ["закономерность 1", "закономерность 2", ...],
    "possible_connections": ["возможная связь 1", "возможная связь 2", ...],
    "positive_changes": ["положительное изменение 1", "положительное изменение 2", ...],
    "areas_to_watch": ["на что обратить внимание 1", "на что обратить внимание 2", ...],
    "next_steps": ["что можно попробовать 1", "что можно попробовать 2", ...],
    "medical_note": "медицинское предостережение или пустая строка"
}
"""

    # ==================== МЕТОДЫ ФОРМИРОВАНИЯ ПРОМПТОВ ====================

    def _build_user_prompt(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> str:
        """Формирует пользовательский промпт для основного анализа."""
        return f"""
Проанализируй следующий симптом и дай структурированный ответ в JSON:

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}

Помни: ты не ставишь диагнозы, а только предлагаешь возможные связи
между симптомом и эмоциональным состоянием.
"""

    def _build_clarification_user_prompt(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        previous_analysis: str,
        history_text: str,
        question: str,
    ) -> str:
        """Формирует промпт для уточняющего вопроса с историей."""
        return f"""
ИСХОДНЫЕ ДАННЫЕ

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}


ПЕРВИЧНЫЙ АНАЛИЗ

{previous_analysis}


ИСТОРИЯ ДИАЛОГА

{history_text if history_text else "Пока нет предыдущих вопросов."}


ТЕКУЩИЙ ВОПРОС

{question}
"""

    def _build_help_dialog_user_prompt(self, message: str, history_text: str = "") -> str:
        """Формирует промпт для свободного диалога."""
        if history_text:
            return f"""
ИСТОРИЯ ДИАЛОГА

{history_text}


ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ

{message}
"""
        else:
            return f"""
ПОЛЬЗОВАТЕЛЬ ПИШЕТ:

{message}

Ответь естественно, как в разговоре. Будь поддерживающим и бережным.
"""

    # ==================== МЕТОДЫ ПАРСИНГА ====================

    def _parse_response(self, response: str) -> AnalysisResult:
        """Парсит ответ YandexGPT в структурированный объект."""
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
            logger.error(f"Failed to parse JSON from YandexGPT: {e}")
            logger.error(f"Response: {response[:500]}")
            return AnalysisResult(
                summary=f"Не удалось распарсить ответ AI. Пожалуйста, попробуйте позже.",
                possible_factors=[],
                possible_patterns=[],
                check_question=None,
                micro_action=None,
                things_to_observe=[],
                medical_warning="Произошла ошибка при обработке ответа. Если симптомы беспокоят, обратитесь к врачу."
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return AnalysisResult(
                summary=f"Произошла ошибка при обработке ответа. Попробуйте позже.",
                possible_factors=[],
                possible_patterns=[],
                check_question=None,
                micro_action=None,
                things_to_observe=[],
                medical_warning="Если симптомы беспокоят, обратитесь к врачу."
            )

    def _parse_dynamics_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Парсит JSON-ответ от YandexGPT для динамики."""
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
                return data
            
            data = json.loads(json_str)

            required_fields = ["summary", "main_patterns", "possible_connections", 
                             "positive_changes", "areas_to_watch", "next_steps"]
            for field in required_fields:
                if field not in data:
                    data[field] = [] if field != "summary" else "Анализ динамики не сформирован."

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in dynamics: {e}")
            logger.error(f"Response: {response[:500]}")
            return None
        except Exception as e:
            logger.error(f"Error parsing dynamics response: {e}")
            return None

    # ==================== РЕЖИМ 1: ПЕРВИЧНЫЙ АНАЛИЗ ТЕЛА ====================

    async def analyze_symptom(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> Dict[str, Any]:
        """Анализирует симптом через YandexGPT (JSON)."""
        logger.info(f"BODY_ANALYSIS_STARTED: symptom={symptom[:30]}..., intensity={intensity}")

        try:
            system_prompt = self._build_primary_system_prompt()
            user_prompt = self._build_user_prompt(
                symptom=symptom,
                duration=duration,
                intensity=intensity,
                context=context,
            )

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,  # Низкая температура для стабильного JSON
            )

            logger.info("BODY_ANALYSIS_COMPLETED")
            
            result = self._parse_response(response)
            
            return {
                "success": True,
                "analysis": result,
                "raw_response": response,
                "error": None,
            }

        except YandexGPTError as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "success": False,
                "analysis": None,
                "raw_response": None,
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            return {
                "success": False,
                "analysis": None,
                "raw_response": None,
                "error": "Произошла непредвиденная ошибка при анализе.",
            }

    # ==================== РЕЖИМ 2: УТОЧНЯЮЩИЕ ВОПРОСЫ ====================

    async def clarify_symptom(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        previous_analysis: str,
        question: str,
        analysis_id: Optional[int] = None,
        telegram_id: Optional[int] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """Отвечает на уточняющий вопрос пользователя (естественный диалог)."""
        logger.info(f"BODY_CLARIFICATION_STARTED: question={question[:30]}...")

        try:
            # Получаем историю предыдущих вопросов
            history_text = ""
            if db_session and analysis_id:
                try:
                    repo = ClarificationRepository(db_session)
                    clarifications = await repo.get_by_analysis_id(analysis_id)
                    if clarifications:
                        history_parts = []
                        for i, clar in enumerate(clarifications, 1):
                            history_parts.append(f"Вопрос {i}: {clar.question}")
                            history_parts.append(f"Ответ {i}: {clar.answer}")
                        history_text = "\n".join(history_parts)
                except Exception as e:
                    logger.warning(f"Could not load clarification history: {e}")

            system_prompt = self._build_clarification_system_prompt()
            user_prompt = self._build_clarification_user_prompt(
                symptom=symptom,
                duration=duration,
                intensity=intensity,
                context=context,
                previous_analysis=previous_analysis,
                history_text=history_text,
                question=question,
            )

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.65,  # Более высокая температура для естественного диалога
            )

            logger.info("BODY_CLARIFICATION_COMPLETED")
            
            result = {
                "success": True,
                "answer": response,
                "raw_response": response,
                "error": None,
            }
            
            # Сохраняем в БД
            if db_session and analysis_id and telegram_id:
                try:
                    user_result = await db_session.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        logger.error(f"User not found for telegram_id: {telegram_id}")
                        result["saved"] = False
                        result["save_error"] = "User not found"
                        return result
                    
                    repo = ClarificationRepository(db_session)
                    
                    clarification = await repo.create(
                        analysis_id=analysis_id,
                        user_id=user.id,
                        question=question,
                        answer=response,
                    )
                    
                    result["saved"] = True
                    result["clarification_id"] = clarification.id
                    
                    logger.info(f"Clarification saved: id={clarification.id}")
                    
                except Exception as e:
                    logger.error(f"Failed to save clarification: {e}")
                    result["saved"] = False
                    result["save_error"] = str(e)
            
            return result

        except YandexGPTError as e:
            logger.error(f"Clarification failed: {e}")
            return {
                "success": False,
                "answer": None,
                "raw_response": None,
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Unexpected clarification error: {e}")
            return {
                "success": False,
                "answer": None,
                "raw_response": None,
                "error": "Произошла ошибка при ответе на вопрос.",
            }

    # ==================== РЕЖИМ 3: «ПОМОГИТЕ РАЗОБРАТЬСЯ» ====================

    async def help_dialog(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Свободный диалог для «Помогите разобраться».
        Не требует JSON, возвращает естественный текст.
        """
        logger.info(f"HELP_DIALOG_STARTED: message={message[:30]}...")

        try:
            # Формируем историю
            history_text = ""
            if history:
                parts = []
                for entry in history:
                    role = "Пользователь" if entry.get("role") == "user" else "AI"
                    content = entry.get("content", "")
                    parts.append(f"{role}: {content}")
                history_text = "\n".join(parts)

            system_prompt = self._build_help_dialog_system_prompt()
            user_prompt = self._build_help_dialog_user_prompt(message, history_text)

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.65,  # Естественный диалог
            )

            logger.info("HELP_DIALOG_MESSAGE_COMPLETED")

            return {
                "success": True,
                "answer": response,
                "raw_response": response,
                "error": None,
            }

        except YandexGPTError as e:
            logger.error(f"Help dialog failed: {e}")
            return {
                "success": False,
                "answer": None,
                "raw_response": None,
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Unexpected help dialog error: {e}")
            return {
                "success": False,
                "answer": None,
                "raw_response": None,
                "error": "Произошла ошибка при ответе.",
            }

    # ==================== ДИНАМИКА ====================

    async def analyze_dynamics(
        self,
        stats: DynamicsStatistics,
    ) -> Optional[DynamicsReport]:
        """Анализ динамики на основе статистики."""
        if stats.entries_count < 3:
            logger.info("Not enough entries for dynamics analysis (need at least 3)")
            return None

        try:
            data_for_ai = self._prepare_dynamics_data(stats)
            system_prompt = self._build_dynamics_system_prompt()
            
            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=json.dumps(data_for_ai, ensure_ascii=False, indent=2),
                temperature=0.3,
            )

            report_data = self._parse_dynamics_response(response)
            if not report_data:
                logger.warning("Failed to parse dynamics response, using fallback")
                return self._create_fallback_report(stats)

            report = DynamicsReport(**report_data)
            
            if not report.medical_note:
                report.medical_note = (
                    "ℹ️ Это наблюдение по дневниковым данным, "
                    "а не доказательство причинно-следственной связи."
                )

            logger.info(f"Dynamics analysis completed for {stats.entries_count} entries")
            return report

        except YandexGPTError as e:
            logger.error(f"YandexGPT error in analyze_dynamics: {e}")
            return self._create_fallback_report(stats)
        except Exception as e:
            logger.error(f"Error in analyze_dynamics: {e}")
            return self._create_fallback_report(stats)

    def _prepare_dynamics_data(self, stats: DynamicsStatistics) -> Dict[str, Any]:
        """Подготовить данные для отправки в AI."""
        data = {
            "period": f"{stats.period_days} дней",
            "period_days": stats.period_days,
            "entries_count": stats.entries_count,
            "start_date": stats.start_date.strftime("%d.%m.%Y"),
            "end_date": stats.end_date.strftime("%d.%m.%Y"),
            
            "average_intensity": stats.average_intensity,
            "min_intensity": stats.min_intensity,
            "max_intensity": stats.max_intensity,
            
            "average_stress": stats.average_stress,
            "min_stress": stats.min_stress,
            "max_stress": stats.max_stress,
            
            "average_mood": stats.average_mood,
            "min_mood": stats.min_mood,
            "max_mood": stats.max_mood,
            
            "average_sleep": stats.average_sleep,
            "min_sleep": stats.min_sleep,
            "max_sleep": stats.max_sleep,
            
            "top_symptoms": [
                {
                    "symptom": s.symptom,
                    "count": s.count,
                    "average_intensity": s.average_intensity,
                    "min_intensity": s.min_intensity,
                    "max_intensity": s.max_intensity,
                }
                for s in stats.top_symptoms
            ],
        }

        if stats.first_period and stats.last_period:
            data["first_period"] = {
                "start": stats.first_period.start_date.strftime("%d.%m.%Y"),
                "end": stats.first_period.end_date.strftime("%d.%m.%Y"),
                "entries_count": stats.first_period.entries_count,
                "average_intensity": stats.first_period.average_intensity,
                "average_stress": stats.first_period.average_stress,
                "average_mood": stats.first_period.average_mood,
                "average_sleep": stats.first_period.average_sleep,
            }
            data["last_period"] = {
                "start": stats.last_period.start_date.strftime("%d.%m.%Y"),
                "end": stats.last_period.end_date.strftime("%d.%m.%Y"),
                "entries_count": stats.last_period.entries_count,
                "average_intensity": stats.last_period.average_intensity,
                "average_stress": stats.last_period.average_stress,
                "average_mood": stats.last_period.average_mood,
                "average_sleep": stats.last_period.average_sleep,
            }

        if stats.stress_symptom_comparison:
            data["stress_comparison"] = stats.stress_symptom_comparison
        if stats.sleep_symptom_comparison:
            data["sleep_comparison"] = stats.sleep_symptom_comparison
        if stats.mood_symptom_comparison:
            data["mood_comparison"] = stats.mood_symptom_comparison

        if stats.relevant_contexts:
            data["recent_contexts"] = stats.relevant_contexts[:3]
        if stats.frequent_contexts:
            data["frequent_contexts"] = stats.frequent_contexts[:3]

        if stats.previous_analyses_summary:
            data["previous_analyses"] = stats.previous_analyses_summary

        return data

    def _create_fallback_report(self, stats: DynamicsStatistics) -> DynamicsReport:
        """Создаёт отчёт-заглушку при ошибке AI."""
        return DynamicsReport(
            summary=(
                f"За {stats.period_days} дней сделано {stats.entries_count} записей. "
                f"Средняя интенсивность симптомов: {stats.average_intensity}/10. "
                f"Средний стресс: {stats.average_stress}/10."
            ),
            main_patterns=[
                f"Интенсивность симптомов варьируется от {stats.min_intensity} до {stats.max_intensity}/10",
                f"Стресс в среднем составляет {stats.average_stress}/10",
            ],
            possible_connections=[],
            positive_changes=[],
            areas_to_watch=[
                "Продолжай отслеживать интенсивность симптомов",
                "Обрати внимание на связь между стрессом и самочувствием",
            ],
            next_steps=[
                "Продолжай вести дневник — это поможет увидеть динамику",
                "Попробуй отслеживать, что влияет на твоё состояние",
            ],
            medical_note="ℹ️ Это наблюдение по дневниковым данным, а не медицинская диагностика.",
        )

    # ==================== МЕТОД АНАЛИЗА С СОХРАНЕНИЕМ ====================

    async def analyze_and_save(
        self,
        telegram_id: int,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """Анализирует симптом и сохраняет результат в БД."""
        logger.info(f"analyze_and_save called: telegram_id={telegram_id}, symptom={symptom[:30]}...")
        
        try:
            result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return {
                    "success": False,
                    "analysis": None,
                    "saved": False,
                    "error": f"Пользователь с telegram_id {telegram_id} не найден",
                }
            
            logger.info(f"User found: id={user.id}, telegram_id={user.telegram_id}")
            
        except Exception as e:
            logger.error(f"Error finding user: {e}")
            return {
                "success": False,
                "analysis": None,
                "saved": False,
                "error": f"Ошибка поиска пользователя: {str(e)}",
            }

        result = await self.analyze_symptom(
            symptom=symptom,
            duration=duration,
            intensity=intensity,
            context=context,
        )

        if not result["success"]:
            result["saved"] = False
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
            
            logger.info(f"Analysis saved to DB: id={analysis.id}, user_id={user.id}")
            
        except Exception as e:
            logger.error(f"Failed to save analysis to DB: {e}")
            result["saved"] = False
            result["save_error"] = str(e)

        return result


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


# Создаем глобальный экземпляр сервиса
ai_service = AIService()