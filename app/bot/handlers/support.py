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
    """Обрабатывает вопрос пользователя."""
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