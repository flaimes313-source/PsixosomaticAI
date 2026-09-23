"""
Обработчик для запуска опросов по кнопке из шедулера.
После перехода на одно утреннее сообщение большинство callback'ов
старых опросов отключено. Здесь обрабатываем только «хвосты» —
старые сообщения, которые ещё могут быть у пользователей.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


# ==================== CALLBACK: survey_start_morning ====================
# ВАЖНО: НЕ обрабатываем здесь — этот callback перехватывает describe_state
# (кнопка «🌿 Описать состояние» из утреннего сообщения)


# ==================== CALLBACK: survey_start_day / survey_start_evening ====================

@router.callback_query(F.data.in_({"survey_start_day", "survey_start_evening"}))
async def start_old_survey_disabled(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """
    Обрабатывает устаревшие callback'и дневного и вечернего опросов.
    Эти опросы больше не используются — сообщаем об этом и удаляем сообщение.
    """
    survey_type = callback.data.replace("survey_start_", "")
    survey_names = {
        "day": "дневной",
        "evening": "вечерний",
    }

    await callback.answer(
        f"{survey_names.get(survey_type, '')} опрос больше не проводится",
        show_alert=False,
    )

    # Удаляем старое сообщение с кнопкой
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Отправляем главное меню
    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text=(
            "🌿 Сейчас доступен только один формат — описать своё состояние. "
            "Нажми «📝 Описать состояние» в меню."
        ),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )

    logger.info(f"Old survey callback '{survey_type}' from user {callback.from_user.id} handled")


# ==================== CALLBACK: survey_skip_* ====================

@router.callback_query(F.data.startswith("survey_skip_"))
async def skip_old_survey(callback: CallbackQuery):
    """Обрабатывает устаревшие callback'и 'Пропустить'."""
    await callback.answer("Ок")

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )

    logger.info(f"Old survey skip callback from user {callback.from_user.id} handled")