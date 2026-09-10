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

    # ==================== ПРОМПТЫ ====================

    def _build_primary_system_prompt(self) -> str:
        """Формирует системный промпт для первичного анализа (JSON)."""
        return """
Ты — AI-помощник «Сома. Забота о себе.»

Ты помогаешь человеку вести ежедневное наблюдение за состоянием: тело, эмоции, мысли, сон, еда, нагрузка, события.
Ты не ставишь диагнозов, не утверждаешь причин, а мягко сопровождаешь.

================================================================================
ВАЖНО! ДЛЯ ПЕРВИЧНОГО АНАЛИЗА ОТВЕЧАЙ ТОЛЬКО В ФОРМАТЕ JSON!
================================================================================

НЕ ПИШИ НИКАКОГО ТЕКСТА ДО И ПОСЛЕ JSON. ТОЛЬКО JSON.

Структура ответа (все ключи строго на английском):
{
    "summary": "Краткое резюме симптома и возможной связи (2-3 предложения)",
    "possible_factors": ["фактор 1", "фактор 2", "фактор 3"],
    "possible_patterns": ["паттерн 1", "паттерн 2"],
    "check_question": "Вопрос для самопроверки (или null)",
    "micro_action": "Маленькое практическое действие (или null)",
    "things_to_observe": ["что наблюдать 1", "что наблюдать 2"],
    "medical_warning": "Медицинское предупреждение или null"
}

ОТВЕЧАЙ ТОЛЬКО JSON. НИКАКОГО ДРУГОГО ТЕКСТА.
"""

    def _build_clarification_system_prompt(self) -> str:
        """Формирует системный промпт для уточняющих вопросов (без JSON)."""
        return """
Ты — AI-помощник проекта «Сома. Забота о себе.»

Пользователь уже прошёл первичный анализ своего состояния.
Сейчас пользователь задаёт уточняющий вопрос.

Отвечай естественным человеческим языком.
Не используй JSON.
Не используй фиксированные разделы.

Отвечай непосредственно на текущий вопрос.
Учитывай исходный симптом, первоначальный анализ и предыдущий диалог.

Ты не врач, не психотерапевт и не ставишь диагнозов.
Твоя задача — бережное сопровождение, повышение осознанности и поддержка внутренней опоры.
"""

    def _build_help_dialog_system_prompt(self) -> str:
        """Формирует системный промпт для свободного диалога «Помогите разобраться»."""
        return """
Ты — AI-помощник проекта «Сома. Забота о себе.»

Ты помогаешь человеку исследовать связь между телесными ощущениями, эмоциями, мыслями, событиями жизни и подсознательными сигналами.

Ты не врач, не психотерапевт и не ставишь диагнозов.

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
"""

    def _build_describe_state_system_prompt(self, context: str = "") -> str:
        """Формирует системный промпт для «Описать состояние» с учётом контекста."""
        base_prompt = """
Ты — AI-помощник «Сома. Забота о себе.»

Ты помогаешь человеку исследовать связь между телесными ощущениями, эмоциями, мыслями, сном, едой, нагрузкой и событиями.

Ты НЕ используешь шаблоны, НЕ даёшь заготовленные ответы, НЕ используешь JSON.

Ты ведёшь живой, естественный диалог. Каждый ответ — уникальный, под конкретного человека и его ситуацию.

Ты не врач, не психотерапевт и не ставишь диагнозов.

Важнейшие принципы:
1. Отвечай естественным человеческим языком.
2. Не используй JSON и фиксированные разделы.
3. Не своди автоматически любой симптом к стрессу или подсознанию.
4. Психосоматические связи описывай только как возможные гипотезы.
5. Не ставь медицинский диагноз.
6. Если есть тревожные симптомы — мягко направь к врачу.
7. Задавай уточняющие вопросы, если нужно прояснить ситуацию.
8. Отвечай на русском языке, просто и понятно.

Стиль общения:
- Дружелюбный, живой, тёплый.
- Без нравоучений.
- Без сложных терминов.
- Поддерживающий.
"""
        
        if context:
            base_prompt += f"""

ИСТОРИЯ ПРЕДЫДУЩИХ РАЗГОВОРОВ С ПОЛЬЗОВАТЕЛЕМ:

{context}

Учитывай эту историю в своём ответе. Если пользователь спрашивает о том, что уже обсуждалось — напомни ему об этом и продолжай тему.
"""
        
        return base_prompt

    def _build_dynamics_system_prompt(self) -> str:
        """Формирует системный промпт для анализа динамики."""
        return """
Ты — AI-помощник проекта «Сома. Забота о себе.»

Ты анализируешь дневниковые наблюдения пользователя и формируешь отчёт о динамике симптомов.

ТЫ НЕ ВРАЧ, НЕ ПСИХОТЕРАПЕВТ, НЕ СТАВИШЬ ДИАГНОЗЫ.

ГЛАВНЫЕ ПРИНЦИПЫ:
1. Анализируй только предоставленные данные.
2. НЕ УТВЕРЖДАЙ ПРИЧИННО-СЛЕДСТВЕННУЮ СВЯЗЬ.
3. Различай корреляцию и причинность.
4. Если данных мало — укажи, что выводы предварительные.

**ОТВЕЧАЙ ТОЛЬКО В ФОРМАТЕ JSON!**

Структура ответа:
{
    "summary": "Общая картина за период",
    "main_patterns": ["закономерность 1"],
    "possible_connections": ["возможная связь 1"],
    "positive_changes": ["положительное изменение 1"],
    "areas_to_watch": ["на что обратить внимание 1"],
    "next_steps": ["что можно попробовать 1"],
    "medical_note": "медицинское предостережение"
}
"""

    # ==================== МЕТОДЫ ФОРМИРОВАНИЯ ПРОМПТОВ ====================

    def _build_user_prompt(self, symptom: str, duration: str, intensity: int, context: str) -> str:
        return f"""
Проанализируй следующий симптом и дай структурированный ответ в JSON:

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}
"""

    def _build_clarification_user_prompt(self, symptom: str, duration: str, intensity: int, context: str, previous_analysis: str, history_text: str, question: str) -> str:
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
"""

    def _build_describe_state_user_prompt(self, description: str) -> str:
        return f"""
Пользователь описывает своё состояние:

{description}

Ответь естественно, как в живом разговоре.
"""

    # ==================== МЕТОДЫ ПАРСИНГА ====================

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
            logger.error(f"Failed to parse JSON from YandexGPT: {e}")
            return AnalysisResult(
                summary="Не удалось распарсить ответ AI.",
                possible_factors=[],
                possible_patterns=[],
                check_question=None,
                micro_action=None,
                things_to_observe=[],
                medical_warning="Произошла ошибка при обработке ответа."
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {e}")
            return AnalysisResult(
                summary="Произошла ошибка при обработке ответа.",
                possible_factors=[],
                possible_patterns=[],
                check_question=None,
                micro_action=None,
                things_to_observe=[],
                medical_warning="Попробуйте позже."
            )

    def _parse_dynamics_response(self, response: str) -> Optional[Dict[str, Any]]:
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
            return None
        except Exception as e:
            logger.error(f"Error parsing dynamics response: {e}")
            return None

    # ==================== КОНТЕКСТ ПОЛЬЗОВАТЕЛЯ ====================

    async def get_user_context(self, telegram_id: int, db_session: AsyncSession, limit: int = 5) -> str:
        try:
            user_result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                return ""
            
            analysis_repo = AnalysisRepository(db_session)
            analyses = await analysis_repo.get_user_analyses(user.id, limit=limit)
            
            if not analyses:
                return ""
            
            context_parts = []
            context_parts.append("📋 Краткая история твоих обращений:\n")
            
            for i, analysis in enumerate(analyses, 1):
                date_str = analysis.created_at.strftime("%d.%m.%Y")
                symptom_preview = analysis.symptom[:80] + "..." if len(analysis.symptom) > 80 else analysis.symptom
                context_parts.append(f"📅 {date_str} — {symptom_preview}")
            
            context_parts.append("")
            context_parts.append("---")
            context_parts.append("")
            
            if analyses:
                last_analysis = analyses[0]
                clar_repo = ClarificationRepository(db_session)
                clarifications = await clar_repo.get_by_analysis_id(last_analysis.id)
                
                if clarifications:
                    context_parts.append("📝 Последние уточнения:")
                    for clar in clarifications[-3:]:
                        context_parts.append(f"❓ {clar.question}")
                        context_parts.append(f"💬 {clar.answer[:100]}...")
                        context_parts.append("")
            
            return "\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return ""

    # ==================== РЕЖИМ 1: АНАЛИЗ СИМПТОМА ====================

    async def analyze_symptom(self, symptom: str, duration: str, intensity: int, context: str) -> Dict[str, Any]:
        logger.info(f"BODY_ANALYSIS_STARTED: symptom={symptom[:30]}...")

        try:
            system_prompt = self._build_primary_system_prompt()
            user_prompt = self._build_user_prompt(symptom, duration, intensity, context)

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
            )

            logger.info("BODY_ANALYSIS_COMPLETED")
            result = self._parse_response(response)
            
            return {"success": True, "analysis": result, "raw_response": response, "error": None}

        except YandexGPTError as e:
            logger.error(f"AI analysis failed: {e}")
            return {"success": False, "analysis": None, "raw_response": None, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            return {"success": False, "analysis": None, "raw_response": None, "error": "Ошибка при анализе."}

    # ==================== РЕЖИМ 2: УТОЧНЕНИЯ ====================

    async def clarify_symptom(self, symptom: str, duration: str, intensity: int, context: str, previous_analysis: str, question: str, analysis_id: Optional[int] = None, telegram_id: Optional[int] = None, db_session: Optional[AsyncSession] = None) -> Dict[str, Any]:
        logger.info(f"BODY_CLARIFICATION_STARTED: question={question[:30]}...")

        try:
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
            user_prompt = self._build_clarification_user_prompt(symptom, duration, intensity, context, previous_analysis, history_text, question)

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.65,
            )

            logger.info("BODY_CLARIFICATION_COMPLETED")
            
            result = {"success": True, "answer": response, "raw_response": response, "error": None}
            
            if db_session and analysis_id and telegram_id:
                try:
                    user_result = await db_session.execute(
                        select(User).where(User.telegram_id == telegram_id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if not user:
                        result["saved"] = False
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
                    # DiaryRepository УДАЛЁН — сохраняем только в DiaryEvent через describe_state.py
                    
                except Exception as e:
                    logger.error(f"Failed to save clarification: {e}")
                    result["saved"] = False
            
            return result

        except YandexGPTError as e:
            logger.error(f"Clarification failed: {e}")
            return {"success": False, "answer": None, "raw_response": None, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected clarification error: {e}")
            return {"success": False, "answer": None, "raw_response": None, "error": "Ошибка при ответе."}

    # ==================== РЕЖИМ 3: HELP DIALOG ====================

    async def help_dialog(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        logger.info(f"HELP_DIALOG_STARTED: message={message[:30]}...")

        try:
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
                temperature=0.65,
            )

            logger.info("HELP_DIALOG_MESSAGE_COMPLETED")
            return {"success": True, "answer": response, "raw_response": response, "error": None}

        except YandexGPTError as e:
            logger.error(f"Help dialog failed: {e}")
            return {"success": False, "answer": None, "raw_response": None, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected help dialog error: {e}")
            return {"success": False, "answer": None, "raw_response": None, "error": "Ошибка при ответе."}

    # ==================== РЕЖИМ 4: ОПИСАТЬ СОСТОЯНИЕ ====================

    async def describe_state(self, description: str, telegram_id: int, db_session: AsyncSession) -> Dict[str, Any]:
        logger.info(f"DESCRIBE_STATE_STARTED: user={telegram_id}, description={description[:30]}...")

        try:
            context = await self.get_user_context(telegram_id, db_session, limit=3)

            system_prompt = self._build_describe_state_system_prompt(context)
            user_prompt = self._build_describe_state_user_prompt(description)

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
                    logger.info(f"Describe state saved to DB: id={analysis.id}, user_id={user.id}")
                    # DiaryRepository УДАЛЁН — сохраняем только в DiaryEvent через describe_state.py
                    
                else:
                    logger.error(f"User not found for telegram_id: {telegram_id}")

            except Exception as e:
                logger.error(f"Failed to save describe state: {e}")

            return {
                "success": True,
                "answer": response,
                "raw_response": response,
                "saved": saved,
                "analysis_id": analysis_id,
                "user_id": user_id,
                "error": None,
            }

        except YandexGPTError as e:
            logger.error(f"Describe state failed: {e}")
            return {"success": False, "answer": None, "raw_response": None, "saved": False, "analysis_id": None, "user_id": None, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected describe state error: {e}")
            return {"success": False, "answer": None, "raw_response": None, "saved": False, "analysis_id": None, "user_id": None, "error": "Ошибка при ответе."}

    # ==================== ДИНАМИКА ====================

    async def analyze_dynamics(self, stats: DynamicsStatistics) -> Optional[DynamicsReport]:
        if stats.entries_count < 3:
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
                return self._create_fallback_report(stats)

            report = DynamicsReport(**report_data)
            
            if not report.medical_note:
                report.medical_note = "ℹ️ Это наблюдение по дневниковым данным."

            return report

        except YandexGPTError as e:
            logger.error(f"YandexGPT error in analyze_dynamics: {e}")
            return self._create_fallback_report(stats)
        except Exception as e:
            logger.error(f"Error in analyze_dynamics: {e}")
            return self._create_fallback_report(stats)

    def _prepare_dynamics_data(self, stats: DynamicsStatistics) -> Dict[str, Any]:
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
        }
        return data

    def _create_fallback_report(self, stats: DynamicsStatistics) -> DynamicsReport:
        return DynamicsReport(
            summary=f"За {stats.period_days} дней сделано {stats.entries_count} записей.",
            main_patterns=[
                f"Интенсивность: {stats.min_intensity}–{stats.max_intensity}/10",
            ],
            possible_connections=[],
            positive_changes=[],
            areas_to_watch=["Продолжай наблюдение"],
            next_steps=["Продолжай вести дневник"],
            medical_note="ℹ️ Это наблюдение по дневниковым данным.",
        )

    # ==================== АНАЛИЗ + СОХРАНЕНИЕ ====================

    async def analyze_and_save(self, telegram_id: int, symptom: str, duration: str, intensity: int, context: str, db_session: AsyncSession) -> Dict[str, Any]:
        logger.info(f"analyze_and_save called: telegram_id={telegram_id}...")
        
        try:
            result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {"success": False, "analysis": None, "saved": False, "error": f"Пользователь не найден"}
            
            logger.info(f"User found: id={user.id}")
            
        except Exception as e:
            logger.error(f"Error finding user: {e}")
            return {"success": False, "analysis": None, "saved": False, "error": str(e)}

        result = await self.analyze_symptom(symptom, duration, intensity, context)

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
            # DiaryRepository УДАЛЁН — сохранение в дневник через DiaryEventService
            
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