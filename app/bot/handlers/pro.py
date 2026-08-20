"""
Обработчик для раздела PRO.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.pro import (
    get_pro_menu_keyboard,
    get_pro_features_keyboard,
    get_pro_upgrade_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.services.access_service import AccessService
from app.services.subscription_service import SubscriptionService
from app.utils.logging import logger

router = Router()


@router.message(F.text == "⭐ PRO")
async def show_pro_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню PRO."""
    await state.clear()
    
    user_id = message.from_user.id
    
    # Получаем информацию о подписке
    access_service = AccessService(db_session)
    subscription_service = SubscriptionService(db_session)
    
    is_pro = await access_service.is_pro(user_id)
    plan_info = await subscription_service.get_subscription_info(user_id)
    
    if is_pro:
        days_left = plan_info.get("days_left")
        if days_left is not None and days_left > 0:
            status_text = f"✅ Активен (осталось {days_left} дн.)"
        else:
            status_text = "✅ Активен (безлимит)"
    else:
        status_text = "🔓 Бесплатный тариф"
    
    text = (
        f"⭐ <b>Psychosomatic PRO</b>\n\n"
        f"Твой тариф: <b>{status_text}</b>\n\n"
        "📋 <b>Что входит в PRO:</b>\n"
        "• 📊 Динамика за 30 и 90 дней\n"
        "• 🔎 Расширенный поиск закономерностей\n"
        "• 📔 Неограниченный дневник\n"
        "• 🧠 Больше AI-анализов (безлимит)\n"
        "• 📈 Расширенные отчёты\n"
        "• 🔔 Расширенные настройки напоминаний\n\n"
        "Стоимость: <b>149 ₽ / месяц</b>"
    )
    
    await message.answer(
        text,
        reply_markup=get_pro_menu_keyboard(is_pro),
        parse_mode="HTML",
    )
    logger.info(f"User opened PRO menu: {user_id}")


@router.callback_query(F.data == "pro_features")
async def show_pro_features(callback: CallbackQuery):
    """Показывает подробности PRO."""
    await callback.answer()
    
    text = (
        "⭐ <b>Что даёт PRO-подписка?</b>\n\n"
        "📊 <b>Анализ динамики</b>\n"
        "• 30 и 90 дней вместо 7\n"
        "• Расширенный анализ закономерностей\n"
        "• Сравнение периодов\n\n"
        "📔 <b>Дневник</b>\n"
        "• Безлимитное количество записей\n"
        "• Расширенная статистика\n\n"
        "🧠 <b>AI-анализы</b>\n"
        "• Неограниченное количество\n"
        "• Расширенные отчёты\n"
        "• Глубокий анализ связей\n\n"
        "🔔 <b>Напоминания</b>\n"
        "• Расширенные настройки\n"
        "• Гибкий график\n\n"
        "💎 Стоимость: <b>149 ₽ / месяц</b>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_features_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_upgrade")
async def show_pro_upgrade(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает страницу подключения PRO."""
    await callback.answer()
    
    user_id = callback.from_user.id
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)
    
    if is_pro:
        text = (
            "⭐ <b>У вас уже есть PRO!</b>\n\n"
            "Статус: ✅ Активен\n\n"
            "Если хотите продлить подписку или изменить настройки — скоро будет доступно."
        )
        await callback.message.edit_text(
            text,
            reply_markup=get_pro_menu_keyboard(True),
            parse_mode="HTML",
        )
        return
    
    text = (
        "💳 <b>Подключить PRO</b>\n\n"
        "⭐ <b>Psychosomatic PRO</b>\n"
        "• 149 ₽ / месяц\n\n"
        "Получи доступ ко всем возможностям:\n"
        "• 📊 Динамика за 30 и 90 дней\n"
        "• 🔎 Расширенный поиск закономерностей\n"
        "• 📔 Неограниченный дневник\n"
        "• 🧠 Больше AI-анализов\n"
        "• 📈 Расширенные отчёты\n"
        "• 🔔 Расширенные настройки\n\n"
        "ℹ️ Оплата будет доступна на следующем этапе.\n"
        "Сейчас можно посмотреть, что входит в PRO."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_upgrade_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_back")
async def back_to_pro_menu(callback: CallbackQuery, db_session: AsyncSession):
    """Возврат в меню PRO."""
    await callback.answer()
    
    user_id = callback.from_user.id
    access_service = AccessService(db_session)
    subscription_service = SubscriptionService(db_session)
    
    is_pro = await access_service.is_pro(user_id)
    plan_info = await subscription_service.get_subscription_info(user_id)
    
    if is_pro:
        days_left = plan_info.get("days_left")
        if days_left is not None and days_left > 0:
            status_text = f"✅ Активен (осталось {days_left} дн.)"
        else:
            status_text = "✅ Активен (безлимит)"
    else:
        status_text = "🔓 Бесплатный тариф"
    
    text = (
        f"⭐ <b>Psychosomatic PRO</b>\n\n"
        f"Твой тариф: <b>{status_text}</b>\n\n"
        "📋 <b>Что входит в PRO:</b>\n"
        "• 📊 Динамика за 30 и 90 дней\n"
        "• 🔎 Расширенный поиск закономерностей\n"
        "• 📔 Неограниченный дневник\n"
        "• 🧠 Больше AI-анализов (безлимит)\n"
        "• 📈 Расширенные отчёты\n"
        "• 🔔 Расширенные настройки напоминаний\n\n"
        "Стоимость: <b>149 ₽ / месяц</b>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_menu_keyboard(is_pro),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_close")
async def close_pro(callback: CallbackQuery, state: FSMContext):
    """Закрывает раздел PRO и возвращает в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )