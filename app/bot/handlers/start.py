"""
Обработчик команды /start.
"""
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.user import UserRepository
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, db_session: AsyncSession, state: FSMContext):
    """
    Обработчик команды /start.
    
    Приоритет: /start всегда очищает FSM состояние.
    """
    tg_user = message.from_user
    
    # Очищаем любое состояние FSM
    await state.clear()
    
    user_repo = UserRepository(db_session)
    
    user = await user_repo.get_or_create(
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
        last_name=tg_user.last_name,
        language_code=tg_user.language_code,
    )
    
    logger.info(f"User started bot: telegram_id={tg_user.id}")
    
    welcome_text = (
        "Привет 👋\n\n"
        "Я помогу тебе разобраться в связи\n"
        "стресса, эмоций и телесных ощущений.\n\n"
        "Важно:\n"
        "я не ставлю диагнозы и не заменяю врача.\n\n"
        "Можем начать с разбора симптома\n"
        "или поговорить о твоём состоянии."
    )
    
    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu_keyboard(),
    )