"""
Обработчик команды /cancel.
"""
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.message(Command("cancel"))
async def cmd_cancel(message: types.Message, state: FSMContext):
    """
    Обработчик команды /cancel.
    
    Очищает состояние FSM и возвращает в главное меню.
    """
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer(
            "У вас нет активного диалога, который можно отменить.",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    # Очищаем состояние
    await state.clear()
    
    # Отправляем сообщение об отмене
    await message.answer(
        "❌ Диалог отменён.\n\n"
        "Возвращаемся в главное меню.",
        reply_markup=get_main_menu_keyboard(),
    )
    
    logger.info(f"User cancelled via /cancel: telegram_id={message.from_user.id}")