"""
Обработчик для кнопки «📝 Описать состояние».
Свободное описание состояния с живым AI-диалогом (без JSON, без шаблонов).
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import DescribeStateStates
from app.bot.keyboards import get_main_menu_keyboard, get_cancel_keyboard
from app.bot.keyboards.pro import get_pro_locked_keyboard
from app.services.ai_service import ai_service
from app.services.access_service import AccessService
from app.services.safety import safety_service, SafetyLevel
from app.db.models.user import User
from app.db.repositories.analysis import AnalysisRepository
from app.utils.logging import logger

router = Router()


@router.message(F.text == "📝 Описать состояние")
async def start_describe_state(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Запускает сценарий «Описать состояние» (живой диалог).
    """
    await state.clear()
    
    telegram_id = message.from_user.id
    
    # Проверяем лимит
    access_service = AccessService(db_session)
    can_use, limit_message = await access_service.can_use_body_analysis(telegram_id)
    
    if not can_use:
        await message.answer(
            limit_message,
            reply_markup=get_pro_locked_keyboard(),
            parse_mode="HTML",
        )
        return
    
    await state.set_state(DescribeStateStates.waiting_for_description)
    
    await message.answer(
        "📝 <b>Расскажи, как ты себя чувствуешь</b>\n\n"
        "Можешь описать тело, эмоции, мысли, сон, еду или нагрузку — что сейчас важно.\n"
        "Если не знаешь, как точно описать — просто напиши своими словами, я помогу уточнить.\n\n"
        "Например:\n"
        "• «Чувствую тяжесть в груди и тревогу»\n"
        "• «Утром болела голова, сейчас легче»\n"
        "• «Не могу сосредоточиться, всё раздражает»\n\n"
        "Я отвечу естественно, без шаблонов — как в живом разговоре.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User started describe state: {telegram_id}")


@router.message(DescribeStateStates.waiting_for_description, F.text)
async def process_describe_state(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обрабатывает описание состояния и запускает живой AI-диалог.
    """
    telegram_id = message.from_user.id
    description = message.text.strip()
    
    if len(description) < 5:
        await message.answer(
            "⚠️ Пожалуйста, опиши состояние подробнее (минимум 5 символов).",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    # SAFETY проверка
    safety_result = safety_service.check_input(description)
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return
    
    loading_message = await message.answer(
        "🧠 Думаю над твоим состоянием...\n\nПожалуйста, подожди.",
        reply_markup=get_cancel_keyboard(),
    )
    
    try:
        # Используем новый метод describe_state
        result = await ai_service.describe_state(
            description=description,
            telegram_id=telegram_id,
            db_session=db_session,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            answer = result["answer"]
            saved = result.get("saved", False)
            analysis_id = result.get("analysis_id")
            
            # Увеличиваем счётчик
            access_service = AccessService(db_session)
            await access_service.increment_body_analysis(telegram_id)
            
            # ==================== ОТВЕТ БЕЗ ШАБЛОНОВ ====================
            result_text = f"🧠 {answer}"
            
            if saved:
                result_text += "\n\n✅ Сохранено в дневник и историю"
            
            # ==================== НОВОЕ: ПЕРЕХОДИМ В РЕЖИМ ПРОДОЛЖЕНИЯ ДИАЛОГА ====================
            await state.update_data(
                analysis_id=analysis_id,
                is_dialog_active=True,
                messages=[{"role": "user", "content": description}, {"role": "assistant", "content": answer}]
            )
            await state.set_state(DescribeStateStates.waiting_for_continue)
            # =================================================================================
            
            # Кнопки для продолжения
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="💬 Продолжить диалог",
                        callback_data="describe_continue"
                    )],
                    [InlineKeyboardButton(
                        text="📝 Новое описание",
                        callback_data="describe_new"
                    )],
                    [InlineKeyboardButton(
                        text="📋 История",
                        callback_data="describe_history"
                    )],
                    [InlineKeyboardButton(
                        text="🔙 В меню",
                        callback_data="describe_back_to_menu"
                    )]
                ]
            )
            
            await message.answer(
                result_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            
            logger.info(f"Describe state completed: user={telegram_id}")
            
        else:
            await message.answer(
                f"😔 Извините, не удалось выполнить анализ.\n\n"
                f"Ошибка: {result.get('error', 'Попробуйте позже.')}\n\n"
                "Попробуйте ещё раз или переформулируйте описание.",
                reply_markup=get_main_menu_keyboard(),
            )
            await state.clear()
            
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Error in describe state: {e}")
        await message.answer(
            "😔 Произошла техническая ошибка. Попробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


# ==================== ПРОДОЛЖЕНИЕ ДИАЛОГА ====================

@router.message(DescribeStateStates.waiting_for_continue, F.text)
async def continue_describe_dialog(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Продолжает диалог «Описать состояние» — пользователь задаёт новый вопрос или уточнение.
    """
    telegram_id = message.from_user.id
    user_text = message.text.strip()
    
    if len(user_text) < 3:
        await message.answer(
            "Пожалуйста, напиши более развёрнутое сообщение (минимум 3 символа).",
            reply_markup=get_continue_dialog_keyboard(),
        )
        return
    
    # SAFETY проверка
    safety_result = safety_service.check_input(user_text)
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return
    
    # Получаем данные из FSM
    data = await state.get_data()
    analysis_id = data.get("analysis_id")
    messages = data.get("messages", [])
    
    # Добавляем сообщение пользователя в историю
    messages.append({"role": "user", "content": user_text})
    
    loading_message = await message.answer(
        "🧠 Думаю...\n\nПожалуйста, подожди.",
        reply_markup=get_continue_dialog_keyboard(),
    )
    
    try:
        # Формируем промпт с учётом истории
        system_prompt = """
Ты — AI-помощник «Сома. Забота о себе.»

Вы продолжаете диалог. Пользователь уже описал своё состояние, и ты ответил.

Теперь пользователь задаёт новый вопрос или уточнение.

Отвечай естественно, как в живом разговоре. Учитывай предыдущий диалог.

Ты не врач, не психотерапевт и не ставишь диагнозов.
Твоя задача — бережное сопровождение и поддержка.

Не используй JSON. Не используй шаблоны.
Будь дружелюбным, тёплым, поддерживающим.
"""
        
        # Формируем историю для AI
        history_text = ""
        for msg in messages:
            role = "Пользователь" if msg.get("role") == "user" else "Ты (AI)"
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"
        
        user_prompt = f"""
ИСТОРИЯ ДИАЛОГА

{history_text}

ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ

{user_text}

Ответь естественно, как в живом разговоре. Учитывай предыдущий диалог.
"""
        
        # Отправляем запрос в YandexGPT
        from app.services.yandex_gpt import YandexGPTClient
        client = YandexGPTClient()
        
        response = await client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=3000,
        )
        
        await loading_message.delete()
        
        # Сохраняем ответ в историю
        messages.append({"role": "assistant", "content": response})
        
        # Сохраняем в БД (как уточнение к анализу)
        try:
            if analysis_id:
                from app.db.repositories.clarification import ClarificationRepository
                from app.db.models.user import User
                
                user_result = await db_session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    clarification_repo = ClarificationRepository(db_session)
                    await clarification_repo.create(
                        analysis_id=analysis_id,
                        user_id=user.id,
                        question=user_text,
                        answer=response,
                    )
                    logger.info(f"Clarification saved for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Failed to save clarification: {e}")
        
        # Обновляем FSM
        await state.update_data(messages=messages)
        
        # Отправляем ответ
        result_text = f"🧠 {response}"
        
        await message.answer(
            result_text,
            reply_markup=get_continue_dialog_keyboard(),
            parse_mode="HTML",
        )
        
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Error in continue dialog: {e}")
        await message.answer(
            "😔 Произошла ошибка. Попробуйте ещё раз.",
            reply_markup=get_continue_dialog_keyboard(),
        )


@router.message(DescribeStateStates.waiting_for_continue)
async def continue_dialog_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод при продолжении диалога."""
    await message.answer(
        "Пожалуйста, напиши текстовое сообщение.",
        reply_markup=get_continue_dialog_keyboard(),
    )


@router.callback_query(F.data == "describe_continue")
async def describe_continue(callback: CallbackQuery, state: FSMContext):
    """Переход в режим продолжения диалога."""
    await callback.answer()
    
    await callback.message.delete()
    
    await callback.message.answer(
        "💬 <b>Продолжаем диалог</b>\n\n"
        "Напиши свой вопрос или уточнение.\n\n"
        "Если хочешь завершить — нажми кнопку ниже.",
        reply_markup=get_continue_dialog_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "describe_finish")
async def describe_finish(callback: CallbackQuery, state: FSMContext):
    """Завершение диалога."""
    await callback.answer("Диалог завершён")
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "✅ Диалог завершён.\n\n"
        "Спасибо, что поделились! 🙏\n\n"
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "describe_new")
async def describe_new(callback: CallbackQuery, state: FSMContext):
    """Начать новое описание."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    
    class FakeMessage:
        def __init__(self, user_id):
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_message = FakeMessage(callback.from_user.id)
    await start_describe_state(fake_message, state, None)


@router.callback_query(F.data == "describe_history")
async def describe_history(callback: CallbackQuery, state: FSMContext):
    """Переход к истории."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.history import show_history
    await show_history(callback, db_session=None)


@router.callback_query(F.data == "describe_back_to_menu")
async def describe_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== КЛАВИАТУРА ДЛЯ ПРОДОЛЖЕНИЯ ====================

def get_continue_dialog_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для продолжения диалога."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Завершить диалог",
                callback_data="describe_finish"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="describe_back_to_menu"
            )]
        ]
    )