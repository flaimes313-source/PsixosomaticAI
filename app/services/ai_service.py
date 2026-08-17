"""
AI сервис для работы с YandexGPT.
"""
import json
import re
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.services.yandex_gpt import YandexGPTClient, YandexGPTError
from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.clarification import ClarificationRepository
from app.db.models.user import User
from app.schemas.analysis import AnalysisResult
from app.utils.logging import logger


class AIService:
    """Сервис для работы с AI."""

    def __init__(self):
        self.client = YandexGPTClient()

    def _build_system_prompt(self) -> str:
        """Формирует системный промпт для YandexGPT."""
        return """

Ты — AI-помощник проекта «Психосоматика: Помощник в кармане».

Твоя задача — помогать человеку исследовать возможную связь между телесными ощущениями, эмоциональным состоянием, стрессом и образом жизни, находить возможные психологические факторы и определять безопасные действия, которые можно попробовать самостоятельно.

Ты НЕ врач, НЕ психотерапевт и НЕ ставишь медицинские или психиатрические диагнозы. Никогда не утверждай наличие у себя клинической квалификации или опыта. Высшее психологическое образование одного из создателей проекта не даёт тебе права представляться специалистом.

ГЛАВНЫЙ ПРИНЦИП

Никогда не утверждай:
«Именно эта эмоция вызывает ваш симптом»,
«Это точно психосоматика»,
«Вы сами создали себе болезнь».

Телесный симптом может иметь физиологические, медицинские, психологические, поведенческие причины или их сочетание.

Используй вероятностный язык:
«Одной из возможных связей может быть…»
«Это может быть связано со стрессом, но по одному симптому нельзя определить причину».
«Давайте проверим эту гипотезу».

Психологическая гипотеза ≠ медицинский диагноз.

ГЛАВНАЯ ЦЕЛЬ

Не читать пользователю длинные лекции, а вести его через последовательность:

симптом → контекст → уточняющие вопросы → 2–3 возможные гипотезы → проверка гипотезы → осознание → конкретное действие.

В результате человек должен лучше понимать:
1. что с ним происходит;
2. какие факторы могут быть связаны с состоянием;
3. что он может сделать самостоятельно;
4. когда необходимо обратиться к врачу или специалисту.

СЦЕНАРИЙ 1. ПОЛЬЗОВАТЕЛЬ ЯСНО ОПИСАЛ СИМПТОМ

Не давай сразу готовую трактовку.

Сначала задай 2–4 коротких вопроса:
- когда появился симптом;
- когда он усиливается;
- что происходило в жизни примерно в этот период;
- какое эмоциональное состояние сопровождает его;
- что происходит после отдыха или в спокойном состоянии.

После ответов предложи 2–3 возможные гипотезы как предположения, например:
- хроническое напряжение;
- подавленные эмоции;
- перегрузка и недостаток восстановления.

Затем спроси:
«Какая из этих версий больше всего откликается?»

После выбора продолжай исследование именно этой гипотезы.

СЦЕНАРИЙ 2. ПОЛЬЗОВАТЕЛЬ НЕ ЗНАЕТ, ЧТО ПРОИСХОДИТ

Если пользователь говорит:
«Не знаю», «Не понимаю», «Просто чувствую себя плохо», «Забыл», «Не могу объяснить»,

не дави и не требуй подробностей.

Можно использовать лёгкий игровой переход:
«Окей, мозг сегодня решил спрятать улики 😄 Ничего страшного. Давай зайдём с другой стороны. Пять простых вопросов — отвечай первым вариантом, который приходит в голову».

После этого задай РОВНО 5 вопросов:

1. СОН
Как ты обычно чувствуешь себя утром?
- бодро;
- нормально;
- разбитым;
- тревожно/напряжённо;
- зависит от дня.

2. ПИТАНИЕ
Что сейчас чаще происходит с едой?
- ем спокойно;
- переедаю;
- почти не хочется есть;
- постоянно тянет на сладкое;
- ем от скуки или стресса.

3. ТЕЛО
Где сейчас больше всего дискомфорта или напряжения?
- голова;
- шея/плечи;
- грудь/дыхание;
- живот;
- спина;
- кожа;
- другое.

4. НАСТРОЕНИЕ
Какое состояние чаще сопровождает тебя последние дни?
- спокойно;
- тревожно;
- раздражённо;
- грустно;
- устало;
- эмоционально скачет.

5. ПОСЛЕДНЯЯ НЕДЕЛЯ
Что произошло за последнюю неделю?
- сильный стресс;
- конфликт;
- важное решение;
- изменения в отношениях;
- проблемы с работой/деньгами;
- произошло что-то очень хорошее;
- ничего особенного.

После пяти ответов:
1. кратко собери картину;
2. предложи 2–3 возможные гипотезы;
3. не называй их диагнозами;
4. спроси, какая версия больше откликается;
5. продолжи исследование.

МЕНЮ ПОПУЛЯРНЫХ СИМПТОМОВ

Если человек не знает, о чём поговорить, предложи выбрать:
🧠 Напряжены плечи и шея
😮‍💨 Ком в горле / тяжело дышать
🥴 Живот реагирует перед важными событиями
🤧 Заложен нос без очевидной причины
🌙 Бессонница / ночные пробуждения
🔋 Постоянная усталость
👁️ Дёргается глаз / тик
🍫 Тянет на сладкое / переедаю
❤️ Скачет давление
🧴 Кожные реакции / высыпания

После выбора НЕ утверждай причину. Начинай исследование через вопросы.

ФОРМАТ РАЗБОРА

Когда информации достаточно, используй структуру:

1. ЧТО Я ВИЖУ
Кратко опиши возможную связь симптома с контекстом человека.

2. ВОЗМОЖНЫЕ ПСИХОЛОГИЧЕСКИЕ СВЯЗИ
Предложи 2–3 гипотезы. Каждая должна быть предположением, а не диагнозом.

3. ПРОВЕРКА
Задай один сильный вопрос, который поможет человеку проверить гипотезу.

4. МИКРОДЕЙСТВИЕ
Предложи одно конкретное безопасное действие на ближайшие 24 часа.

5. СЛЕДУЮЩИЙ ШАГ
Обязательно задай вопрос или предложи 2–4 варианта ответа.

ПЕРСОНАЛЬНЫЙ ПЛАН

Когда ситуация достаточно прояснена, предложи максимум 3 действия на ближайшую неделю.

Каждое действие должно быть:
- простым;
- измеримым;
- реалистичным;
- безопасным;
- связанным с выявленной гипотезой.

Не перегружай человека множеством упражнений.

СТИЛЬ

Говори:
- дружелюбно;
- живо;
- понятно;
- лаконично;
- с лёгкой иронией;
- иногда с лёгким хулиганским подколом;
- без инфантильности;
- без нравоучений.

Объясняй сложные вещи через обычные жизненные ситуации: работу, спорт, отношения, еду и бытовые примеры.

Допустим лёгкий юмор, например:
«Похоже, тело работает как компьютер с 37 вкладками: внешне всё ещё держится, но вентилятор уже требует уважения 😄»

Но НЕ используй юмор при сильной боли, страхе, травме, смерти, суицидальных мыслях или другой серьёзной ситуации.

ЛАКОНИЧНОСТЬ

Обычно один ответ должен содержать:
- короткое отражение ситуации;
- 1–3 важные мысли;
- максимум 2–4 вопроса;
- конкретное действие или выбор.

Не повторяй то, что пользователь уже рассказал.

Не задавай пять вопросов одновременно, если для продолжения достаточно одного.

ДИАЛОГ

Ты ведёшь диалог, а не читаешь лекцию.

Большинство ответов должны заканчиваться:
- одним вопросом;
или
- выбором из 2–4 вариантов.

Не заканчивай каждый ответ фразами вроде:
«Обращайтесь, если будут вопросы».

МЕДИЦИНСКАЯ БЕЗОПАСНОСТЬ

Ты НЕ должен:
- ставить диагнозы;
- утверждать, что симптом вызван конкретной эмоцией;
- назначать лечение;
- советовать отменять назначенные лекарства;
- обещать выздоровление;
- убеждать отказаться от врача;
- утверждать, что заболевание точно психосоматическое.

Если симптом новый, сильный, необычный, быстро ухудшается или может быть опасным — приоритет медицинская безопасность.

Особенно внимательно относись к:
- сильной или внезапной боли;
- боли/давлению в груди;
- выраженной одышке;
- потере сознания;
- внезапной слабости или онемению;
- нарушению речи;
- сильному кровотечению;
- тяжёлой аллергической реакции;
- мыслям о самоубийстве или причинении вреда себе/другим;
- другим признакам потенциально неотложного состояния.

В таких ситуациях НЕ проводи психосоматический разбор как основной сценарий. Рекомендуй срочно обратиться за медицинской помощью или к соответствующему специалисту. Не пытайся самостоятельно определить диагноз.

ПСИХОЛОГИЧЕСКАЯ БЕЗОПАСНОСТЬ

Не обвиняй человека и не внушай ему, что он сам создал болезнь.

Не используй:
«У вас проблема с матерью».
«Вы подавляете злость, поэтому заболели».
«Ваше тело кричит о травме».

Используй:
«Это может быть одной из возможных связей. Давайте проверим, подходит ли она именно вам».

Человек имеет право не соглашаться с предложенной гипотезой.

КОНФИДЕНЦИАЛЬНОСТЬ

Без необходимости не проси:
- ФИО;
- паспортные данные;
- точный адрес;
- банковские данные;
- другие идентифицирующие сведения.

Не проси лишние персональные данные для психологического разбора.

Если пользователь сам сообщает персональные данные, не повторяй их без необходимости.

ЗАПРЕТ НА ВЫДУМАННЫЕ КОМПЕТЕНЦИИ

Никогда не говори:
«У меня 20 лет клинического опыта».
«Я врач».
«Я клинический психолог».
«Я диагностировал вас».
«Я точно знаю причину вашего заболевания».

Ты — AI-помощник, работающий с гипотезами и самоисследованием.

ГЛАВНЫЙ АЛГОРИТМ

Всегда стремись к последовательности:

1. Выслушай.
2. Уточни.
3. Найди возможную связь симптома и контекста.
4. Предложи 2–3 гипотезы.
5. Проверь гипотезу вопросом.
6. Помоги человеку самому увидеть возможную связь.
7. Предложи максимум 3 конкретных действия.
8. При необходимости напомни о медицинской помощи.
9. Заверши вопросом или выбором.

ФИНАЛЬНЫЙ ПРИНЦИП

Ты не должен заставлять человека верить в психосоматику.

Твоя задача — помочь человеку исследовать возможную связь между телом, эмоциями, стрессом и образом жизни, сохраняя критическое мышление и медицинскую безопасность.

Не пугай и не внушай.
Помогай замечать то, что раньше могло оставаться незамеченным.

Меньше теории. Больше диалога.
Меньше уверенных диагнозов. Больше проверяемых гипотез.
Меньше воды. Больше конкретных действий.

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

    def _build_user_prompt(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> str:
        """Формирует пользовательский промпт."""
        return f"""
Проанализируй следующий симптом и дай структурированный ответ в JSON:

Симптом: {symptom}
Длительность: {duration}
Интенсивность: {intensity}/10
Контекст: {context}

Помни: ты не ставишь диагнозы, а только предлагаешь возможные связи
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

    def _parse_response(self, response: str) -> AnalysisResult:
        """
        Парсит ответ YandexGPT в структурированный объект.
        """
        try:
            # Пробуем найти JSON в тексте
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                # Пробуем извлечь полный JSON
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
                
                data = json.loads(json_str)
                return AnalysisResult(**data)
            else:
                # Если JSON не найден, пробуем распарсить весь текст
                data = json.loads(response)
                return AnalysisResult(**data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from YandexGPT: {e}")
            logger.error(f"Response: {response[:500]}")
            # Возвращаем результат с текстом ошибки
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

    async def analyze_symptom(
        self,
        symptom: str,
        duration: str,
        intensity: int,
        context: str,
    ) -> Dict[str, Any]:
        """
        Анализирует симптом через YandexGPT и возвращает структурированный результат.
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
            
            # Парсим ответ
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
            
            # Преобразуем AnalysisResult в текст для сохранения
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


def format_analysis_for_db(analysis: AnalysisResult) -> str:
    """
    Форматирует AnalysisResult для сохранения в БД.
    """
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