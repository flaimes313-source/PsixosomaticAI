"""
Обработчик для «🧠 Помогите разобраться».
Свободный AI-диалог с YandexGPT.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import HelpDialogStates
from app.bot.keyboards import get_main_menu_keyboard
from app.services.ai_service import ai_service
from app.services.access_service import AccessService
from app.services.safety import safety_service, SafetyLevel
from app.db.repositories.help_dialog_repository import HelpDialogRepository
from app.db.models.user import User
from app.utils.logging import logger

router = Router()


@router.message(F.text == "🧠 Помогите разобраться")
async def start_help_dialog(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Запуск свободного AI-диалога «Помогите разобраться».
    """
    await state.clear()
    
    telegram_id = message.from_user.id
    
    # ==================== ПРОВЕРКА ЛИМИТА ====================
    access_service = AccessService(db_session)
    can_use, limit_message = await access_service.can_use_help_dialog(telegram_id)
    
    if not can_use:
        # Показываем кнопку PRO
        pro_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="⭐ Подключить PRO",
                    callback_data="pro_pay"
                )],
                [InlineKeyboardButton(
                    text="🔙 В меню",
                    callback_data="help_back_to_menu"
                )]
            ]
        )
        await message.answer(
            limit_message,
            reply_markup=pro_keyboard,
            parse_mode="HTML",
        )
        return
    # =========================================================
    
    # ==================== СОЗДАЁМ НОВУЮ СЕССИЮ ====================
    repo = HelpDialogRepository(db_session)
    session_id = await repo.create_session(telegram_id)
    
    await state.update_data(
        session_id=session_id,
        is_active=True,
        messages=[],
    )
    await state.set_state(HelpDialogStates.waiting_for_message)
    # =============================================================
    
    await message.answer(
        "🧠 <b>Помогите разобраться</b>\n\n"
        "Расскажи, что тебя беспокоит, — я постараюсь помочь.\n"
        "Ты можешь задавать вопросы, уточнять, возвращаться к теме.\n\n"
        "Просто напиши сообщение — и продолжим диалог.\n\n"
        "Когда захочешь завершить — нажми кнопку ниже.",
        reply_markup=get_help_dialog_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"HELP_DIALOG_STARTED: user={telegram_id}, session={session_id}")


@router.message(HelpDialogStates.waiting_for_message, F.text)
async def process_help_message(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обрабатывает сообщение пользователя в диалоге «Помогите разобраться».
    """
    telegram_id = message.from_user.id
    user_text = message.text.strip()
    
    if not user_text or len(user_text) < 3:
        await message.answer(
            "Пожалуйста, напиши более развёрнутое сообщение (минимум 3 символа).",
            reply_markup=get_help_dialog_keyboard(),
        )
        return
    
    # ==================== SAFETY ПРОВЕРКА ====================
    safety_result = safety_service.check_input(user_text)
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return
    # ========================================================
    
    # ==================== ПОЛУЧАЕМ ДАННЫЕ ИЗ FSM ====================
    data = await state.get_data()
    session_id = data.get("session_id")
    messages_history = data.get("messages", [])
    # ================================================================
    
    # ==================== СОХРАНЯЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ ====================
    repo = HelpDialogRepository(db_session)
    await repo.add_message(
        user_id=telegram_id,
        session_id=session_id,
        role="user",
        content=user_text,
    )
    # ========================================================================
    
    # ==================== ПОЛУЧАЕМ ИСТОРИЮ ИЗ БД ====================
    history = await repo.get_session_history(telegram_id, session_id, limit=20)
    history_for_ai = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    # =================================================================
    
    # ==================== ОТПРАВЛЯЕМ ЗАПРОС К AI ====================
    loading_message = await message.answer(
        "🧠 Думаю...\n\nПожалуйста, подождите.",
        reply_markup=get_help_dialog_keyboard(),
    )
    
    try:
        result = await ai_service.help_dialog(
            message=user_text,
            history=history_for_ai[:-1] if len(history_for_ai) > 1 else None,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            ai_answer = result["answer"]
            
            # ==================== SAFETY ПРОВЕРКА ОТВЕТА ====================
            safety_output = safety_service.check_output(ai_answer)
            if safety_output.level == SafetyLevel.CRITICAL:
                await message.answer(
                    safety_output.warning or "⚠️ Не удалось безопасно сформировать ответ.",
                    reply_markup=get_main_menu_keyboard(),
                )
                await state.clear()
                return
            # ==============================================================
            
            # ==================== СОХРАНЯЕМ ОТВЕТ AI ====================
            await repo.add_message(
                user_id=telegram_id,
                session_id=session_id,
                role="assistant",
                content=ai_answer,
            )
            # ============================================================
            
            # ==================== ОБНОВЛЯЕМ FSM ====================
            await state.update_data(messages=messages_history + [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": ai_answer},
            ])
            # ========================================================
            
            await message.answer(
                f"🧠 {ai_answer}",
                reply_markup=get_help_dialog_keyboard(),
                parse_mode="HTML",
            )
            
        else:
            error_msg = result.get("error", "Неизвестная ошибка")
            await message.answer(
                f"😔 Извините, не удалось получить ответ.\n\nОшибка: {error_msg}\n\nПопробуйте переформулировать вопрос.",
                reply_markup=get_help_dialog_keyboard(),
            )
            
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Unexpected error in help dialog: {e}")
        await message.answer(
            "😔 Произошла техническая ошибка. Попробуйте ещё раз.",
            reply_markup=get_help_dialog_keyboard(),
        )


@router.message(HelpDialogStates.waiting_for_message)
async def process_help_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод (не текст)."""
    await message.answer(
        "Пожалуйста, напишите текстовое сообщение.",
        reply_markup=get_help_dialog_keyboard(),
    )


@router.callback_query(F.data == "help_finish")
async def finish_help_dialog(callback: CallbackQuery, state: FSMContext):
    """
    Завершает диалог «Помогите разобраться».
    """
    await callback.answer("Диалог завершён")
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "✅ Диалог завершён.\n\n"
        "Спасибо, что обратились! 🙏\n"
        "Вы всегда можете начать новый разговор.\n\n"
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )
    logger.info(f"HELP_DIALOG_FINISHED: user={callback.from_user.id}")


@router.callback_query(F.data == "help_back_to_menu")
async def help_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== КЛАВИАТУРА ====================

def get_help_dialog_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для диалога «Помогите разобраться»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Завершить диалог",
                callback_data="help_finish"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="help_back_to_menu"
            )]
        ]
    )