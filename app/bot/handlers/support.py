"""
Обработчик раздела поддержки.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import SupportStates
from app.bot.keyboards.support import (
    get_support_menu_keyboard,
    get_support_cancel_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.models.support import SupportRequest
from app.db.models.user import User
from app.utils.logging import logger

router = Router()

# ID админа для оповещений
ADMIN_ID = 462035571


@router.message(F.text == "❓ Поддержка")
async def show_support_menu(message: types.Message, state: FSMContext):
    """Показывает меню поддержки."""
    await state.clear()
    
    await message.answer(
        "❓ <b>Поддержка</b>\n\n"
        "Здесь ты можешь задать любой вопрос.\n"
        "Мы ответим тебе в ближайшее время.\n\n"
        "📝 Напиши свой вопрос ниже:",
        reply_markup=get_support_menu_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(SupportStates.waiting_for_question)


@router.message(SupportStates.waiting_for_question, F.text)
async def process_support_question(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает вопрос пользователя и отправляет оповещение админу."""
    question = message.text.strip()
    
    if question.startswith('/'):
        return
    
    if len(question) < 5:
        await message.answer(
            "⚠️ Пожалуйста, напиши вопрос подробнее (минимум 5 символов).",
            reply_markup=get_support_cancel_keyboard(),
        )
        return
    
    # Сохраняем обращение в БД
    support_request = SupportRequest(
        user_id=message.from_user.id,
        message=question,
        is_answered=False,
    )
    db_session.add(support_request)
    await db_session.commit()
    
    # Сохраняем ID обращения в FSM
    await state.update_data(request_id=support_request.id)
    
    # Ответ пользователю
    await message.answer(
        "✅ <b>Ваше обращение отправлено!</b>\n\n"
        "Мы ответим вам в ближайшее время.\n"
        "Ответ придёт в этот чат.\n\n"
        "🆔 Номер обращения: <b>#{}</b>".format(support_request.id),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    await state.clear()
    
    logger.info(f"Support request created: id={support_request.id}, user={message.from_user.id}")
    
    # ==================== ОПОВЕЩЕНИЕ АДМИНА ====================
    try:
        # Получаем имя пользователя
        user_result = await db_session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user_result.scalar_one_or_none()
        user_name = user.first_name if user else "Неизвестно"
        
        # Отправляем оповещение админу
        await message.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📩 <b>НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ!</b>\n\n"
                f"🆔 <b>#{support_request.id}</b>\n"
                f"👤 Пользователь: <code>{message.from_user.id}</code>\n"
                f"👤 Имя: {user_name}\n"
                f"📝 Вопрос:\n{question}\n\n"
                f"➡️ <b>Ответить:</b> /answer {support_request.id} <текст>"
            ),
            parse_mode="HTML",
        )
        logger.info(f"✅ Admin notified about support request #{support_request.id}")
    except Exception as e:
        logger.error(f"❌ Failed to notify admin: {e}")


@router.message(SupportStates.waiting_for_question)
async def process_support_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в поддержке."""
    await message.answer(
        "Пожалуйста, напиши свой вопрос текстом.",
        reply_markup=get_support_cancel_keyboard(),
    )


@router.callback_query(F.data == "support_cancel")
async def cancel_support(callback: CallbackQuery, state: FSMContext):
    """Отмена обращения в поддержку."""
    await callback.answer("Отменяем...")
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )