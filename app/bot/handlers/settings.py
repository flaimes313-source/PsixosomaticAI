"""
Обработчик раздела "Настройки".
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.bot.keyboards.settings import (
    get_settings_keyboard,
    get_confirm_delete_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.models.user import User
from app.db.models.analysis import Analysis
from app.db.models.clarification import Clarification
from app.db.models.diary_event import DiaryEvent
from app.db.models.reminder import ReminderSettings
from app.db.models.subscription import Subscription
from app.utils.logging import logger

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: types.Message, state: FSMContext):
    """Показывает меню настроек."""
    await state.clear()

    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете управлять своими данными.\n\n"
        "Доступные действия:",
        reply_markup=get_settings_keyboard(back_to="menu"),
        parse_mode="HTML",
    )
    logger.info(f"User opened settings: {message.from_user.id}")


# ==================== ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ ====================

@router.callback_query(F.data == "delete_all_data")
async def confirm_delete_data(callback: CallbackQuery):
    """Подтверждение удаления данных."""
    await callback.answer()

    await callback.message.edit_text(
        "🗑 <b>Удаление всех данных</b>\n\n"
        "Вы действительно хотите удалить все свои данные?\n\n"
        "Будут удалены:\n"
        "• Все диалоги «Описать состояние»\n"
        "• Все уточняющие вопросы и ответы\n"
        "• Все записи дневника и история\n"
        "• Настройки напоминаний\n"
        "• История подписок\n\n"
        "⚠️ Это действие <b>нельзя отменить</b>!\n\n"
        "ℹ️ Профиль сохранится, но все наблюдения будут удалены.",
        reply_markup=get_confirm_delete_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_data(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Отмена удаления данных."""
    await callback.answer("Удаление отменено")

    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Удаление данных отменено.",
        reply_markup=get_settings_keyboard(back_to="menu"),
        parse_mode="HTML",
    )


# ==================== УДАЛЕНИЕ ДАННЫХ ====================

@router.callback_query(F.data == "confirm_delete_all")
async def delete_all_user_data(callback: CallbackQuery, db_session: AsyncSession):
    """
    Удаляет все данные пользователя, но СОХРАНЯЕТ самого User.

    Удаляем:
    - diary_events, clarifications, analyses, reminder_settings, subscriptions.
    НЕ трогаем:
    - users (обнуляем флаги trial/free_dialog/счётчики),
      payments, pro_whitelist, support_requests, broadcasts.
    """
    await callback.answer("Удаление данных...")

    telegram_id = callback.from_user.id

    try:
        # ==================== 1. ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЯ ====================
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.message.edit_text(
                "⚠️ Пользователь не найден.",
                reply_markup=None,
            )
            return

        user_id = user.id  # внутренний ID

        # ==================== 2. УДАЛЯЕМ ДАННЫЕ (в порядке FK) ====================

        # 2.1. Clarifications (FK → analyses, users)
        result_clarifications = await db_session.execute(
            delete(Clarification).where(Clarification.user_id == user_id)
        )
        clarifications_deleted = result_clarifications.rowcount

        # 2.2. DiaryEvent (FK → users, analyses)
        result_diary_events = await db_session.execute(
            delete(DiaryEvent).where(DiaryEvent.user_id == user_id)
        )
        diary_events_deleted = result_diary_events.rowcount

        # 2.3. Analyses (FK → users)
        result_analyses = await db_session.execute(
            delete(Analysis).where(Analysis.user_id == user_id)
        )
        analyses_deleted = result_analyses.rowcount

        # 2.4. ReminderSettings (по telegram_id)
        result_reminders = await db_session.execute(
            delete(ReminderSettings).where(ReminderSettings.user_id == telegram_id)
        )
        reminders_deleted = result_reminders.rowcount

        # 2.5. Subscriptions (по telegram_id)
        result_subscription = await db_session.execute(
            delete(Subscription).where(Subscription.user_id == telegram_id)
        )
        subscription_deleted = result_subscription.rowcount

        # ==================== 3. ОБНУЛЯЕМ ФЛАГИ И СЧЁТЧИКИ В USERS ====================

        user.trial_used = False
        user.trial_started_at = None
        user.trial_ends_at = None
        user.free_dialog_used = False
        user.free_dialog_questions_count = 0
        user.body_analysis_count = 0
        user.body_analysis_month = None
        user.help_analysis_count = 0
        user.help_analysis_month = None
        user.diary_entries_count = 0

        await db_session.commit()

        logger.info(
            f"All user data deleted: telegram_id={telegram_id}, "
            f"diary_events={diary_events_deleted}, "
            f"analyses={analyses_deleted}, "
            f"clarifications={clarifications_deleted}, "
            f"reminders={reminders_deleted}, "
            f"subscription={subscription_deleted}"
        )

        # ==================== 4. СООБЩАЕМ ПОЛЬЗОВАТЕЛЮ ====================

        await callback.message.edit_text(
            "✅ <b>Все данные удалены.</b>\n\n"
            "Удалены:\n"
            f"• {diary_events_deleted} записей диалогов\n"
            f"• {analyses_deleted} анализов\n"
            f"• {clarifications_deleted} уточнений\n"
            f"• {reminders_deleted} настроек напоминаний\n"
            f"• {subscription_deleted} записей подписок\n\n"
            "🌿 Твой профиль сохранён. Все наблюдения удалены.\n\n"
            "Можешь начать заново — нажми «📝 Описать состояние» "
            "или отправь /start.",
            reply_markup=None,
            parse_mode="HTML",
        )

    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error deleting user data: {e}", exc_info=True)
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при удалении данных. Попробуйте ещё раз позже.",
            reply_markup=None,
        )


# ==================== ВОЗВРАТ ====================

@router.callback_query(F.data == "back_to_menu_from_settings")
async def back_to_menu_from_settings(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню из настроек."""
    await callback.answer()
    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "settings_back_to_profile")
async def back_to_profile_from_settings(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в профиль из настроек."""
    await callback.answer()
    await state.clear()

    from app.bot.handlers.profile import show_profile_from_callback

    try:
        await callback.message.delete()
    except Exception:
        pass

    await show_profile_from_callback(callback, state, db_session)