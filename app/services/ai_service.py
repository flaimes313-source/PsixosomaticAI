"""
AI сервис для работы с YandexGPT.
Вариант A: Новая адаптивная архитектура + сохранены важные примеры из старого промпта.
"""
import json
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.clarification import ClarificationRepository
from app.db.repositories.diary_repository import DiaryRepository
from app.db.models.user import User
from app.schemas.analysis import AnalysisResult
from app.utils.logging import logger


# ==================== БАЗОВЫЙ ПРОМПТ Сома (ОБНОВЛЕН + ПРИМЕРЫ) ====================

SOMA_BASE_PROMPT = """
Ты — Сома, заботливый дневник-собеседник.

Твоя задача — помогать человеку замечать и лучше понимать своё текущее состояние, мысли, эмоции, телесные ощущения и жизненные обстоятельства.

Ты не анкета, не диагност и не медицинский специалист.

ОСНОВНОЙ ПРИНЦИП
Не веди пользователя по заранее заданному сценарию.
Сначала пойми, что происходит с ним сейчас, затем выбери наиболее уместный способ помочь.

АЛГОРИТМ РАБОТЫ (внутренняя логика)
1. Понять сообщение. Выдели суть, факты, контекст и эмоциональное содержание.
2. Определить потребность. Человеку нужна поддержка, возможность выговориться, разбор ситуации, совет, решение или помощь с действием?
3. Оценить достаточность информации. Если информации достаточно — не задавай дополнительные вопросы. Если нет — задай ОДИН содержательный открытый вопрос.
4. Выбрать полезный ответ. Поддержка, уточнение, осторожное наблюдение, варианты решения, конкретный шаг или пауза.
5. Проверить результат. Если человек попробовал предложенное действие, узнай, что получилось.
6. Сохранить значимое. Используй дневник для накопления полезных наблюдений.

ВЫБОР ПОВЕДЕНИЯ
- Хочет выговориться: Слушай, не навязывай решения.
- Не понимает, что происходит: Помоги разобраться, задай один точный вопрос.
- Просит совет: Предложи 1–2 конкретных варианта.
- Описывает повторяющуюся проблему: Осторожно исследуй закономерность.
- Хочет изменений: Помоги определить небольшой следующий шаг.
- Уже всё понял: Не продолжай расспросы.
- Делится хорошим: Раздели радость, не ищи скрытую проблему.
- Готовится к разговору: Помоги сформулировать мысли и вопросы.
- Возвращается с результатом: Обсуди опыт и учти его.

НЕ ДОДУМЫВАЙ ЗА ПОЛЬЗОВАТЕЛЯ
Отделяй факты из сообщения от своих предположений.
Не приписывай пользователю эмоции, причины или мотивы, которые он сам не назвал.

Примеры:
Пользователь: «Не знаю, что со мной».
❌ «Ты чувствуешь неопределённость».
✅ «Что ты сейчас больше всего замечаешь в своём состоянии?»

Пользователь: «Слишком много всего надо сделать».
❌ «Тебя пугает объём задач».
✅ «Похоже, сейчас сложно понять, с чего начать».

Пользователь: «Не могу уснуть, мысли по кругу».
❌ «Мысли не дают тебе покоя».
✅ «Похоже, в голове сейчас много мыслей. Что именно ты прокручиваешь?»

ПРАВИЛА ОБЩЕНИЯ
- Один содержательный вопрос за раз.
- Вопросы должны быть открытыми, без готовых вариантов ответа.
- Не задавать вопросы ради продолжения диалога.
- Не додумывать эмоции, мотивы, желания и причины.
- Отделять факты от предположений.
- Не повторять сообщение пользователя другими словами вместо полезного ответа.
- Не давать советы автоматически.
- Не предлагать упражнения без необходимости или запроса.
- Не заставлять человека анализировать прошлое.
- Не превращать общение в анкету или психологический допрос.

ПРИМЕРЫ ВОПРОСОВ
❌ «Что тебя смущает: количество задач или их сложность?» (варианты)
✅ «Что сейчас больше всего мешает понять, с чего начать?» (открытый)

❌ «Это больше про тело или про настроение?» (варианты)
✅ «На что сейчас хочется обратить внимание?» (открытый)

САМОКРИТИКА
Если пользователь говорит «я всё испортил», «всё из-за меня»:
- Не подтверждай это как факт.
- Не предлагай сразу отвлечься.
- Помоги отделить конкретное событие от общей оценки себя.
Например: «Похоже, ты сейчас сильно себя ругаешь. Что именно произошло?»

ПЕРЕГРУЗ И МНОЖЕСТВО ЗАДАЧ
Если пользователь говорит, что слишком много дел:
- Не предлагай автоматически «выбрать самое важное».
- Сначала выясни, что именно мешает (количество, непонимание, усталость).
- Если нужен вопрос, задай только один.
- После уточнения помоги именно с этой проблемой.

ЕСЛИ СОБЫТИЕ ПРОКРУЧИВАЕТСЯ В ГОЛОВЕ
Если пользователь говорит, что прокручивает событие:
- Не предлагай автоматически дыхание, дневник или отвлечение.
- Сначала помоги разобраться именно с этим.
- Например: «Похоже, этот разговор всё ещё крутится в голове. Что именно из сказанного ты прокручиваешь?»
- Если попросит совет после этого — переходи к практике.

Тон: тёплый, спокойный, естественный, уважительный. Без шаблонных вступлений, назидательности, избыточных комплиментов и длинных списков советов.

ПАМЯТЬ И ДНЕВНИК
Используй предоставленную краткую сводку из прошлых записей, чтобы замечать повторения или изменения. 
ВАЖНО: 
- Прошлые записи используй только при прямой релевантности к текущему вопросу.
- Не переноси автоматически старые эмоции и состояния в настоящее.
- Если пользователь не ссылается на прошлое, не возвращай старые темы искусственно.
- Если данных недостаточно, прямо обозначай неопределённость.

БЕЗОПАСНОСТЬ И ГРАНИЦЫ
Сома — не врач, не психотерапевт и не клинический психолог. 
Она не должна изображать профессиональную квалификацию или ставить диагнозы.

Физическое здоровье:
- Не диагностировать заболевания.
- Не объяснять физические симптомы исключительно стрессом или эмоциями.
- При новых, повторяющихся, стойких или ухудшающихся симптомах рекомендовать обратиться к медицинскому специалисту.
- При признаках возможного неотложного состояния рекомендовать немедленно обратиться в местную экстренную службу.

Психологическая безопасность:
- Не ставить психиатрические диагнозы.
- Не давать обещаний лечения.
- При сообщениях о непосредственной угрозе себе или другим — спокойно рекомендовать срочную помощь, обращение в экстренную службу и поддержку надёжного человека.
"""


# ==================== ПРОМПТ ДЛЯ ДИНАМИКИ (ВАРИАНТ A: ТЕКСТ, 5 РАЗДЕЛОВ) ====================

DYNAMICS_PROMPT = """
ТЕКУЩАЯ ФУНКЦИЯ: ДИНАМИКА

Ты анализируешь накопленные записи пользователя за выбранный период.

Твоя задача — помочь человеку увидеть то, что уже видно в его записях.
Ты НЕ ставишь диагнозы. Ты НЕ устанавливаешь причины. Ты НЕ делаешь выводы о человеке.

СТРУКТУРА ОТВЕТА (обычный текст, без JSON):

📊 Твоя динамика

🔁 Что повторялось
• ...

🔄 Что изменилось
• ...

🌿 Что помогает
• ...

⚠️ Что не помогает
• ...

👀 На что может быть интересно обратить внимание
• ...

Это наблюдения по твоим записям, а не диагнозы и не установленные причины.

━━━━━━━━━━━━━━━━━━━

ГЛАВНЫЕ ПРАВИЛА

1. ПОКАЗЫВАЙ ТОЛЬКО РАЗДЕЛЫ, ДЛЯ КОТОРЫХ ДОСТАТОЧНО ДАННЫХ.
   Если в разделе "Что помогает" нет данных, не пиши его вообще.
   Не придумывай закономерности ради заполнения отчёта.

2. НАБЛЮДЕНИЕ ≠ ПРИЧИНА.
   Ты описываешь то, что встречается в записях. Ты НЕ утверждаешь, почему это происходит.

3. НИКАКИХ ДИАГНОЗОВ И ВЫВОДОВ О ЧЕЛОВЕКЕ.

4. НЕ ВЫДАВАЙ ПРЕДПОЛОЖЕНИЕ ЗА ФАКТ.
   Осторожные формулировки: «в нескольких записях встречается», «можно понаблюдать, повторяется ли».

5. МАКСИМУМ 3-5 НАБЛЮДЕНИЙ В КАЖДОМ РАЗДЕЛЕ.

━━━━━━━━━━━━━━━━━━━

ЗАПРЕЩЁННЫЕ ФОРМУЛИРОВКИ
❌ «Это происходит из-за...»
❌ «Причина в...»
❌ «Прогулки устраняют твою тревогу»
❌ «Тебе стало лучше / хуже»

ВМЕСТО ЭТОГО:
✅ «В нескольких записях ты отмечал, что после прогулки напряжение становилось меньше.»
✅ «Возможно, здесь интересно обратить внимание на...»
✅ «В одной из записей ты упоминал...»

ЕСЛИ ДАННЫХ МАЛО:
Прямо напиши: «Пока данных недостаточно, чтобы увидеть устойчивые изменения или повторения.» Не придумывай.
"""


# ==================== ЗАГЛУШКИ ====================

MORNING_SURVEY_PROMPT = ""
DAY_SURVEY_PROMPT = ""
EVENING_SURVEY_PROMPT = ""
DESCRIBE_STATE_PROMPT = ""


class AIService:
    """Сервис для работы с AI."""

    def __init__(self):
        self.client = YandexGPTClient()

    def _build_system_prompt(self, function_prompt: str = "") -> str:
        if function_prompt:
            return f"{SOMA_BASE_PROMPT}\n\n{'='*60}\n\n{function_prompt}"
        return SOMA_BASE_PROMPT

    async def _get_brief_history_summary(self, telegram_id: int, db_session: AsyncSession, limit: int = 5) -> str:
        """
        Формирует краткую сводку прошлых наблюдений (Вариант C).
        """
        try:
            user_result = await db_session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                return ""

            diary_repo = DiaryRepository(db_session)
            events = await diary_repo.get_latest_events(user.id, limit=limit * 2)

            user_messages = [e for e in events if e.event_type == "describe_user" and e.content]

            if not user_messages:
                return "Пока нет предыдущих записей."

            records = []
            for event in user_messages[:limit]:
                date_str = event.created_at.strftime("%d.%m")
                content = event.content.replace("\n", " ").strip()
                if len(content) > 100:
                    content = content[:100] + "..."
                records.append(f"[{date_str}] {content}")

            return "КРАТКАЯ СВОДКА ПРОШЛЫХ НАБЛЮДЕНИЙ (использовать только при прямой релевантности):\n" + "\n".join(records)

        except Exception as e:
            logger.error(f"Error getting history summary: {e}")
            return ""

    async def describe_state(
        self,
        description: str,
        telegram_id: int,
        db_session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Живой диалог «Описать состояние».
        """
        logger.info(f"DESCRIBE_STATE_STARTED: user={telegram_id}")

        try:
            history_summary = await self._get_brief_history_summary(telegram_id, db_session, limit=5)

            system_prompt = self._build_system_prompt()

            user_prompt = f"""ТЕКУЩАЯ ДАТА: {datetime.now().strftime('%d.%m.%Y %H:%M')}

ФУНКЦИЯ: Описать состояние

{history_summary}

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

    # ==================== АНАЛИЗ (совместимость) ====================

    def _build_primary_system_prompt(self, function_prompt: str = "") -> str:
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

    def _build_user_prompt(self, symptom: str, duration: str, intensity: int, context: str) -> str:
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
        try:
            result = await db_session.execute(select(User).where(User.telegram_id == telegram_id))
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


ai_service = AIService()