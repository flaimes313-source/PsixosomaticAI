"""
AI сервис для работы с YandexGPT.
"""
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.db.repositories.analysis import AnalysisRepository
from app.db.models.user import User
from app.utils.logging import logger


class AIService:
    """Сервис для работы с AI."""

    def __init__(self):
        self.client = YandexGPTClient()

    def _build_system_prompt(self) -> str:
        """Формирует системный промпт для YandexGPT."""
        return """
Ты — психосоматический помощник.

Твоя задача — помочь пользователю исследовать возможную связь
между его физическими симптомами и психоэмоциональным состоянием.

Правила:
1. НЕ СТАВЬ МЕДИЦИНСКИЕ ДИАГНОЗЫ
2. Не давай медицинских рекомендаций
3. Говори бережно и поддерживающе
4. Основывайся на психосоматическом подходе
5. Предлагай практические действия для снижения стресса

Структура ответа:
1. Краткое резюме симптома
2. Возможная психосоматическая связь (2-3 гипотезы)
3. Рекомендации по работе с состоянием
4. Когда обратиться к врачу

Важно: Всегда напоминай, что это не медицинский диагноз.
"""

    def _build_user_prompt(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> str:
        """Формирует пользовательский промпт."""
        return f"""
Пользователь обратился с таким симптомом:

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}

Пожалуйста, дай бережный психосоматический анализ
этого симптома на основе предоставленной информации.

Помни: ты не ставишь диагнозы,
а только предлагаешь возможные связи
между симптомом и эмоциональным состоянием.
"""

    def _build_clarification_prompt(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        previous_analysis: str,
        question: str,
    ) -> str:
        """
        Формирует промпт для уточняющего вопроса.
        """
        return f"""
Ранее пользователь обратился с таким симптомом:

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}

Твой предыдущий анализ:
{previous_analysis}

Теперь пользователь задает уточняющий вопрос:
"{question}"

Ответь на вопрос пользователя, основываясь на контексте.
Будь бережным, не ставь диагнозов.
"""

    async def analyze_symptom(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> Dict[str, Any]:
        """
        Анализирует симптом через YandexGPT (без сохранения в БД).
        """
        logger.info(f"AI analysis started: symptom={symptom[:30]}..., intensity={intensity}")

        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(
                symptom=symptom,
                duration=duration,
                intensity=intensity,
                context=context,
            )

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            logger.info("AI analysis completed successfully")

            return {
                "success": True,
                "analysis": response,
                "error": None,
            }

        except YandexGPTError as e:
            logger.error(f"AI analysis failed: {e}")
            return {
                "success": False,
                "analysis": None,
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Unexpected AI error: {e}")
            return {
                "success": False,
                "analysis": None,
                "error": "Произошла непредвиденная ошибка при анализе.",
            }

    async def clarify_symptom(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        previous_analysis: str,
        question: str,
        analysis_id: Optional[int] = None,
        user_id: Optional[int] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Отвечает на уточняющий вопрос пользователя и сохраняет в БД.
        """
        logger.info(f"Clarification started: question={question[:30]}...")

        try:
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_clarification_prompt(
                symptom=symptom,
                duration=duration,
                intensity=intensity,
                context=context,
                previous_analysis=previous_analysis,
                question=question,
            )

            response = await self.client.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            logger.info("Clarification completed successfully")
            
            result = {
                "success": True,
                "answer": response,
                "error": None,
            }
            
            # Сохраняем в БД, если переданы параметры
            if db_session and analysis_id and user_id:
                try:
                    from app.db.repositories.clarification import ClarificationRepository
                    repo = ClarificationRepository(db_session)
                    
                    clarification = await repo.create(
                        analysis_id=analysis_id,
                        user_id=user_id,
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
                "error": str(e),
            }

        except Exception as e:
            logger.error(f"Unexpected clarification error: {e}")
            return {
                "success": False,
                "answer": None,
                "error": "Произошла ошибка при ответе на вопрос.",
            }

    async def analyze_and_save(
        self,
        telegram_id: int,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Анализирует симптом и сохраняет результат в БД.
        """
        logger.info(f"analyze_and_save called: telegram_id={telegram_id}, symptom={symptom[:30]}...")
        
        # Находим пользователя
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

        # Получаем анализ от AI
        result = await self.analyze_symptom(
            symptom=symptom,
            duration=duration,
            intensity=intensity,
            context=context,
        )

        if not result["success"]:
            result["saved"] = False
            return result

        # Сохраняем в БД
        try:
            analysis_repo = AnalysisRepository(db_session)
            
            analysis = await analysis_repo.create(
                user_id=user.id,
                symptom=symptom,
                duration=duration,
                intensity=intensity,
                context=context,
                analysis=result["analysis"],
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


# Создаем глобальный экземпляр сервиса
ai_service = AIService()