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
from app.db.models.diary import DiaryEntry
from app.db.models.reminder import ReminderSettings
from app.db.models.subscription import Subscription
from app.db.models.usage import UserUsage
from app.utils.logging import logger

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: types.Message, state: FSMContext):
    """Показывает меню настроек (по умолчанию с возвратом в меню)."""
    await state.clear()
    
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете управлять своими данными.\n\n"
        "Доступные действия:",
        reply_markup=get_settings_keyboard(back_to="menu"),
        parse_mode="HTML",
    )
    logger.info(f"User opened settings: {message.from_user.id}")


async def show_settings_edit(message: types.Message, state: FSMContext, callback: CallbackQuery = None):
    """
    Показывает настройки с редактированием текущего сообщения (из профиля).
    """
    await state.clear()
    
    text = (
        "⚙️ <b>Настройки</b>\n\n"
        "Здесь вы можете управлять своими данными.\n\n"
        "Доступные действия:"
    )
    
    if callback:
        await callback.message.edit_text(
            text,
            reply_markup=get_settings_keyboard(back_to="profile"),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            text,
            reply_markup=get_settings_keyboard(back_to="profile"),
            parse_mode="HTML",
        )
    logger.info(f"User opened settings from profile: {message.from_user.id}")


# ==================== ОБРАБОТЧИКИ ====================

@router.callback_query(F.data == "delete_all_data")
async def confirm_delete_data(callback: CallbackQuery):
    """Подтверждение удаления данных."""
    await callback.answer()
    
    await callback.message.edit_text(
        "🗑 <b>Удаление всех данных</b>\n\n"
        "Вы действительно хотите удалить все свои данные?\n\n"
        "Будут удалены:\n"
        "• Все анализы симптомов\n"
        "• Все уточняющие вопросы и ответы\n"
        "• Все записи дневника\n"
        "• Настройки напоминаний\n"
        "• История подписок\n"
        "• Статистика использования\n\n"
        "⚠️ Это действие <b>нельзя отменить</b>!",
        reply_markup=get_confirm_delete_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete_data(callback: CallbackQuery):
    """Отмена удаления данных."""
    await callback.answer("Удаление отменено")
    
    # Определяем, откуда пришли (из меню или из профиля)
    # По умолчанию возвращаем в меню
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "Удаление данных отменено.",
        reply_markup=get_settings_keyboard(back_to="menu"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "confirm_delete_all")
async def delete_all_user_data(callback: CallbackQuery, db_session: AsyncSession):
    """Удаляет все данные пользователя."""
    await callback.answer("Удаление данных...")
    
    telegram_id = callback.from_user.id
    
    try:
        # Находим пользователя
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
        
        user_id = user.id
        
        # ==================== КАСКАДНОЕ УДАЛЕНИЕ ====================
        
        # 1. Удаляем уточнения (Clarification)
        result_clarifications = await db_session.execute(
            delete(Clarification).where(Clarification.user_id == user_id)
        )
        clarifications_deleted = result_clarifications.rowcount
        
        # 2. Удаляем анализы (Analysis)
        result_analyses = await db_session.execute(
            delete(Analysis).where(Analysis.user_id == user_id)
        )
        analyses_deleted = result_analyses.rowcount
        
        # 3. Удаляем записи дневника (DiaryEntry)
        result_diary = await db_session.execute(
            delete(DiaryEntry).where(DiaryEntry.user_id == user_id)
        )
        diary_deleted = result_diary.rowcount
        
        # 4. Удаляем настройки напоминаний (ReminderSettings)
        result_reminders = await db_session.execute(
            delete(ReminderSettings).where(ReminderSettings.user_id == telegram_id)
        )
        reminders_deleted = result_reminders.rowcount
        
        # 5. Удаляем подписку (Subscription)
        result_subscription = await db_session.execute(
            delete(Subscription).where(Subscription.user_id == telegram_id)
        )
        subscription_deleted = result_subscription.rowcount
        
        # 6. Удаляем статистику использования (UserUsage)
        result_usage = await db_session.execute(
            delete(UserUsage).where(UserUsage.user_id == telegram_id)
        )
        usage_deleted = result_usage.rowcount
        
        # 7. Удаляем пользователя (User)
        await db_session.delete(user)
        await db_session.commit()
        
        logger.info(
            f"All user data deleted: telegram_id={telegram_id}, "
            f"analyses={analyses_deleted}, "
            f"clarifications={clarifications_deleted}, "
            f"diary={diary_deleted}, "
            f"reminders={reminders_deleted}, "
            f"subscription={subscription_deleted}, "
            f"usage={usage_deleted}"
        )
        
        await callback.message.edit_text(
            "✅ <b>Все ваши данные удалены.</b>\n\n"
            "Удалены:\n"
            f"• {analyses_deleted} анализов\n"
            f"• {clarifications_deleted} уточнений\n"
            f"• {diary_deleted} записей дневника\n"
            f"• {reminders_deleted} настройки напоминаний\n"
            f"• {subscription_deleted} история подписок\n"
            f"• {usage_deleted} статистика использования\n\n"
            "Вы можете начать заново, отправив /start",
            reply_markup=None,
            parse_mode="HTML",
        )
        
    except Exception as e:
        await db_session.rollback()
        logger.error(f"Error deleting user data: {e}")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при удалении данных. Попробуйте ещё раз позже.",
            reply_markup=None,
        )


# ==================== ВОЗВРАТ В ГЛАВНОЕ МЕНЮ ====================

@router.callback_query(F.data == "back_to_menu_from_settings")
async def back_to_menu_from_settings(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню из настроек."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== ВОЗВРАТ В ПРОФИЛЬ ====================

@router.callback_query(F.data == "settings_back_to_profile")
async def back_to_profile_from_settings(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в профиль из настроек."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.profile import show_profile
    
    await callback.message.delete()
    await show_profile(callback.message, state, db_session)