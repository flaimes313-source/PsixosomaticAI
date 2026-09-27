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
from app.db.repositories.reminder import ReminderRepository
from app.db.repositories.diary_repository import DiaryRepository
from app.services.access_service import AccessService
from app.services.subscription_service import SubscriptionService
from app.utils.logging import logger

router = Router()


# ==================== ОСНОВНОЙ ПОКАЗ ПРОФИЛЯ ====================

@router.message(F.text == "👤 Профиль")
async def show_profile(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает профиль пользователя."""
    await state.clear()

    user_id = message.from_user.id

    result = await db_session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        from app.db.repositories.user import UserRepository
        user_repo = UserRepository(db_session)
        user = await user_repo.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )
        user.timezone = "Europe/Moscow"
        await db_session.commit()
        await db_session.refresh(user)

    access_service = AccessService(db_session)
    subscription_service = SubscriptionService(db_session)

    is_pro = await access_service.is_pro(user_id)
    plan_info = await subscription_service.get_subscription_info(user_id)

    if is_pro:
        days_left = plan_info.get("days_left")
        if days_left is not None and days_left > 0:
            plan_status = f"⭐ PRO (осталось {days_left} дн.)"
        else:
            plan_status = "⭐ PRO (безлимит)"
    else:
        plan_status = "🔓 Демо (FREE)"

    reminder_repo = ReminderRepository(db_session)
    reminder = await reminder_repo.get_or_create(user_id)

    logger.info(
        f"[PROFILE] user={user_id}, "
        f"reminder_enabled={reminder.enabled}, "
        f"reminder_time={reminder.reminder_time}, "
        f"updated_at={reminder.updated_at}"
    )

    if reminder.enabled and reminder.reminder_time:
        reminder_status = f"✅ {reminder.reminder_time.strftime('%H:%M')}"
    elif reminder.enabled:
        reminder_status = "✅ 09:00 (по умолчанию)"
    else:
        reminder_status = "❌ Выключено"

    created_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"

    diary_repo = DiaryRepository(db_session)
    events_count = await diary_repo.count_user_events(user.id)

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
        f"🔔 <b>Утреннее сообщение:</b> {reminder_status}\n"
        f"📔 <b>Записей в дневнике:</b> {events_count}\n\n"
        "Выбери раздел для управления:"
    )

    await message.answer(
        text,
        reply_markup=get_profile_menu_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User opened profile: {user_id}")


# ==================== ПОКАЗ ПРОФИЛЯ ИЗ CALLBACK ====================

async def show_profile_from_callback(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Показывает профиль пользователя из callback."""
    await state.clear()

    user_id = callback.from_user.id

    result = await db_session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        from app.db.repositories.user import UserRepository
        user_repo = UserRepository(db_session)
        user = await user_repo.get_or_create(
            telegram_id=user_id,
            username=callback.from_user.username,
            first_name=callback.from_user.first_name,
            last_name=callback.from_user.last_name,
            language_code=callback.from_user.language_code,
        )
        user.timezone = "Europe/Moscow"
        await db_session.commit()
        await db_session.refresh(user)

    access_service = AccessService(db_session)
    subscription_service = SubscriptionService(db_session)

    is_pro = await access_service.is_pro(user_id)
    plan_info = await subscription_service.get_subscription_info(user_id)

    if is_pro:
        days_left = plan_info.get("days_left")
        if days_left is not None and days_left > 0:
            plan_status = f"⭐ PRO (осталось {days_left} дн.)"
        else:
            plan_status = "⭐ PRO (безлимит)"
    else:
        plan_status = "🔓 Демо (FREE)"

    reminder_repo = ReminderRepository(db_session)
    reminder = await reminder_repo.get_or_create(user_id)

    logger.info(
        f"[PROFILE_FROM_CALLBACK] user={user_id}, "
        f"reminder_enabled={reminder.enabled}, "
        f"reminder_time={reminder.reminder_time}, "
        f"updated_at={reminder.updated_at}"
    )

    if reminder.enabled and reminder.reminder_time:
        reminder_status = f"✅ {reminder.reminder_time.strftime('%H:%M')}"
    elif reminder.enabled:
        reminder_status = "✅ 09:00 (по умолчанию)"
    else:
        reminder_status = "❌ Выключено"

    created_date = user.created_at.strftime("%d.%m.%Y") if user.created_at else "Неизвестно"

    diary_repo = DiaryRepository(db_session)
    events_count = await diary_repo.count_user_events(user.id)

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
        f"🔔 <b>Утреннее сообщение:</b> {reminder_status}\n"
        f"📔 <b>Записей в дневнике:</b> {events_count}\n\n"
        "Выбери раздел для управления:"
    )

    await callback.message.answer(
        text,
        reply_markup=get_profile_menu_keyboard(),
        parse_mode="HTML",
    )

    logger.info(f"User opened profile from callback: {user_id}")


# ==================== ОБРАБОТЧИК ДЕЙСТВИЙ В ПРОФИЛЕ ====================

@router.callback_query(F.data.startswith("profile_"))
async def profile_menu_actions(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession = None):
    """Обработка действий в профиле."""
    await callback.answer()

    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await _handle_profile_action(callback, state, new_session)
        return

    await _handle_profile_action(callback, state, db_session)


async def _handle_profile_action(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Внутренний обработчик действий в профиле."""
    action = callback.data.replace("profile_", "")
    logger.info(f"[PROFILE_ACTION] user={callback.from_user.id}, action={action}")

    if action == "back_to_profile":
        await callback.message.delete()
        await show_profile_from_callback(callback, state, db_session)
        return

    if action == "back_to_menu":
        await callback.message.delete()
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    elif action == "settings":
        await callback.message.delete()
        from app.bot.handlers.settings import show_settings
        await show_settings(callback.message, state, back_to="profile")

    elif action == "reminders":
        await callback.message.delete()
        from app.bot.handlers.reminders import show_reminders_from_profile
        await show_reminders_from_profile(
            callback.message,
            state,
            db_session,
            telegram_id=callback.from_user.id,
        )

    elif action == "subscription":
        await callback.message.delete()
        from app.bot.handlers.pro import show_pro_from_profile
        await show_pro_from_profile(
            callback.message,
            state,
            db_session,
            telegram_id=callback.from_user.id,
        )

    elif action == "history":
        await callback.message.delete()
        from app.bot.handlers.history import show_history
        await show_history(callback, db_session, state)

    elif action == "privacy":
        privacy_text = (
            "🔐 <b>Конфиденциальность</b>\n\n"
            "Мы сохраняем технические данные,\n"
            "необходимые для работы бота:\n"
            "• Telegram ID\n"
            "• Имя и фамилия\n"
            "• Время взаимодействия\n"
            "• История анализов\n\n"
            "Вы можете удалить все свои данные\n"
            "в разделе ⚙️ Управление данными.\n\n"
            "Важно: бот не ставит медицинские диагнозы\n"
            "и не заменяет профессиональную помощь."
        )
        await callback.message.edit_text(
            privacy_text,
            reply_markup=get_profile_back_keyboard(),
            parse_mode="HTML",
        )

    elif action == "help":
        help_text = (
            "❓ <b>Справка</b>\n\n"

            "📝 <b>Описать состояние</b>\n"
            "Расскажи Соме, что ты сейчас замечаешь. Она поможет разобраться "
            "и задаст необходимые уточняющие вопросы.\n\n"

            "📔 <b>Дневник</b>\n"
            "Здесь сохраняются твои наблюдения и диалоги с Сомой.\n\n"

            "📜 <b>История</b>\n"
            "Позволяет вернуться к прошлым диалогам и посмотреть их содержание.\n\n"

            "📊 <b>Динамика</b>\n"
            "Помогает увидеть, что повторялось, что изменилось "
            "и на что может быть интересно обратить внимание.\n\n"

            "🔔 <b>Напоминания</b>\n"
            "Здесь можно настроить утреннее напоминание или отключить его.\n\n"

            "⭐ <b>PRO</b>\n"
            "Здесь можно посмотреть текущий статус подписки, выбрать тариф PRO "
            "и оплатить подписку.\n\n"

            "👤 <b>Профиль</b>\n"
            "Здесь можно посмотреть информацию о своём профиле, статус подписки, "
            "настройки напоминаний, управление данными и другие доступные разделы.\n\n"

            "💬 <b>Поддержка</b>\n"
            "Здесь можно обратиться за помощью по работе бота или задать свой вопрос.\n\n"

            "⚠️ Сома не ставит диагнозы и не заменяет врача."
        )
        await callback.message.edit_text(
            help_text,
            reply_markup=get_profile_back_keyboard(),
            parse_mode="HTML",
        )


# ==================== ВОЗВРАТ В ПРОФИЛЬ ====================

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile_generic(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession = None):
    """Универсальный возврат в профиль."""
    await callback.answer()
    await state.clear()
    await callback.message.delete()

    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await show_profile_from_callback(callback, state, new_session)
    else:
        await show_profile_from_callback(callback, state, db_session)


@router.callback_query(F.data == "history_back_to_profile")
async def history_back_to_profile(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession = None):
    """Возврат в профиль из истории."""
    await callback.answer()
    await state.clear()
    await callback.message.delete()

    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await show_profile_from_callback(callback, state, new_session)
    else:
        await show_profile_from_callback(callback, state, db_session)