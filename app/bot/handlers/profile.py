"""
Обработчик раздела "Профиль".
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from zoneinfo import ZoneInfo

from app.bot.keyboards.profile import (
    get_profile_menu_keyboard,
    get_profile_back_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.models.user import User
from app.db.models.subscription import Subscription, PlanType
from app.db.models.reminder import ReminderSettings
from app.services.access_service import AccessService
from app.services.subscription_service import SubscriptionService
from app.utils.logging import logger

router = Router()


@router.message(F.text == "👤 Профиль")
async def show_profile(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает профиль пользователя."""
    await state.clear()
    
    user_id = message.from_user.id
    
    # Получаем данные пользователя
    result = await db_session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer(
            "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    # Получаем информацию о подписке
    access_service = AccessService(db_session)
    subscription_service = SubscriptionService(db_session)
    
    is_pro = await access_service.is_pro(user_id)
    plan_info = await subscription_service.get_subscription_info(user_id)
    
    # Определяем статус подписки
    if is_pro:
        days_left = plan_info.get("days_left")
        if days_left is not None and days_left > 0:
            plan_status = f"⭐ PRO (осталось {days_left} дн.)"
        else:
            plan_status = "⭐ PRO (безлимит)"
    else:
        plan_status = "🔓 Демо (FREE)"
    
    # Получаем настройки напоминаний
    reminder_result = await db_session.execute(
        select(ReminderSettings).where(ReminderSettings.user_id == user_id)
    )
    reminder = reminder_result.scalar_one_or_none()
    
    if reminder and reminder.enabled and reminder.reminder_time:
        reminder_status = f"✅ {reminder.reminder_time.strftime('%H:%M')}"
    else:
        reminder_status = "❌ Выключены"
    
    # Формируем текст профиля
    created_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"
    
    # Определяем часовой пояс
    try:
        tz = ZoneInfo(user.timezone) if user.timezone else ZoneInfo("UTC")
        current_time = datetime.now(tz).strftime("%H:%M")
        timezone_display = user.timezone or "UTC"
    except:
        current_time = datetime.now().strftime("%H:%M")
        timezone_display = "UTC"
    
    text = (
        "👤 <b>Мой профиль</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"👤 Имя: {user.first_name or 'Не указано'}\n"
        f"📅 Дата регистрации: {created_date}\n"
        f"🌍 Часовой пояс: {timezone_display}\n"
        f"⏰ Текущее время: {current_time}\n\n"
        f"💳 <b>Подписка:</b> {plan_status}\n"
        f"🔔 <b>Напоминания:</b> {reminder_status}\n\n"
        "Выбери раздел для управления:"
    )
    
    await message.answer(
        text,
        reply_markup=get_profile_menu_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User opened profile: {user_id}")


@router.callback_query(F.data.startswith("profile_"))
async def profile_menu_actions(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обработка действий в профиле."""
    await callback.answer()
    
    action = callback.data.replace("profile_", "")
    
    if action == "back":
        await callback.message.edit_text(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        await callback.message.delete()
        return
    
    elif action == "settings":
        # Перенаправляем в настройки
        from app.bot.handlers.settings import show_settings
        await callback.message.delete()
        await show_settings(callback.message, state)
    
    elif action == "reminders":
        # Перенаправляем в напоминания
        from app.bot.handlers.reminders import show_reminders_menu
        await callback.message.delete()
        await show_reminders_menu(callback.message, state, db_session)
    
    elif action == "privacy":
        # Показываем конфиденциальность
        privacy_text = (
            "🔐 <b>Конфиденциальность</b>\n\n"
            "Мы сохраняем технические данные,\n"
            "необходимые для работы бота:\n"
            "• Telegram ID\n"
            "• Имя и фамилия\n"
            "• Время взаимодействия\n"
            "• История анализов\n\n"
            "Вы можете удалить все свои данные\n"
            "в разделе ⚙️ Настройки.\n\n"
            "Важно: бот не ставит медицинские диагнозы\n"
            "и не заменяет профессиональную помощь."
        )
        await callback.message.edit_text(
            privacy_text,
            reply_markup=get_profile_back_keyboard(),
            parse_mode="HTML",
        )
    
    elif action == "subscription":
        # Перенаправляем в PRO
        from app.bot.handlers.pro import show_pro_menu
        await callback.message.delete()
        await show_pro_menu(callback.message, state, db_session)
    
    elif action == "back_to_profile":
        # Возврат в профиль
        await callback.message.delete()
        # Перезапускаем профиль
        await show_profile(callback.message, state, db_session)