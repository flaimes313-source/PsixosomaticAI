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
    get_pro_payment_keyboard,
    get_pro_success_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.bot.states import ProStates
from app.services.access_service import AccessService
from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService
from app.utils.logging import logger
from app.config import settings

router = Router()


@router.message(F.text == "⭐ PRO")
async def show_pro_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню PRO."""
    await state.clear()
    
    user_id = message.from_user.id
    
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
        f"💳 Стоимость: <b>{settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>"
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
        f"💳 Стоимость: <b>{settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_features_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_pay")
async def start_payment(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Начинает процесс оплаты PRO."""
    await callback.answer("Создаю платёж...")
    
    user_id = callback.from_user.id
    
    # Проверяем, не PRO ли уже
    access_service = AccessService(db_session)
    if await access_service.is_pro(user_id):
        await callback.message.edit_text(
            "⭐ У вас уже есть PRO!\n\n"
            "Хотите продлить? Нажмите 'Продлить' в меню.",
            reply_markup=get_pro_menu_keyboard(True),
            parse_mode="HTML",
        )
        return
    
    # Создаём платёж
    payment_service = PaymentService(db_session)
    result = await payment_service.create_pro_payment(user_id)
    
    if not result.get("success"):
        await callback.message.edit_text(
            f"❌ Не удалось создать платёж.\n\n{result.get('error', 'Попробуйте позже.')}",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # Сохраняем payment_id в FSM
    await state.set_state(ProStates.waiting_for_payment)
    await state.update_data(payment_id=result.get("payment_id"))
    
    # Показываем ссылку на оплату
    confirmation_url = result.get("confirmation_url")
    amount = result.get("amount")
    
    text = (
        f"💳 <b>Оплата PRO</b>\n\n"
        f"Сумма: <b>{amount} ₽</b>\n"
        f"Период: <b>{settings.PRO_DURATION_DAYS} дней</b>\n\n"
        "Нажми на кнопку ниже, чтобы перейти к оплате.\n"
        "После оплаты PRO активируется автоматически.\n\n"
        "⏳ Ожидай подтверждения в течение нескольких минут."
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_payment_keyboard(confirmation_url),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Проверяет статус платежа."""
    await callback.answer("Проверяю...")
    
    data = await state.get_data()
    payment_id = data.get("payment_id")
    
    if not payment_id:
        await callback.message.edit_text(
            "❌ Платёж не найден. Попробуйте начать заново.",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    payment_service = PaymentService(db_session)
    payment_info = await payment_service.get_payment_info(payment_id, callback.from_user.id)
    
    if not payment_info:
        await callback.message.edit_text(
            "❌ Платёж не найден.",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    status = payment_info.get("status")
    
    if status == "succeeded":
        await state.clear()
        await callback.message.edit_text(
            "🎉 <b>Оплата прошла успешно!</b>\n\n"
            "⭐ PRO активирован!\n\n"
            f"Доступ до: <b>{payment_info.get('expires_at').strftime('%d.%m.%Y') if payment_info.get('expires_at') else 'бессрочно'}</b>",
            reply_markup=get_pro_success_keyboard(),
            parse_mode="HTML",
        )
    elif status == "pending":
        await callback.message.edit_text(
            "⏳ <b>Платёж в обработке...</b>\n\n"
            "Ожидай подтверждения. Обычно это занимает несколько минут.\n\n"
            "Нажми 'Проверить' через минуту.",
            reply_markup=get_pro_payment_keyboard(None),
            parse_mode="HTML",
        )
    else:
        await callback.message.edit_text(
            f"❌ <b>Статус платежа: {status}</b>\n\n"
            "Платёж не завершён. Попробуй ещё раз.",
            reply_markup=get_pro_features_keyboard(),
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
        f"💳 Стоимость: <b>{settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>"
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


@router.callback_query(F.data == "pro_payments_history")
async def show_payments_history(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает историю платежей."""
    await callback.answer()
    
    user_id = callback.from_user.id
    payment_service = PaymentService(db_session)
    payments = await payment_service.get_user_payments(user_id, limit=10)
    
    if not payments:
        await callback.message.edit_text(
            "💳 <b>История платежей</b>\n\n"
            "У вас пока нет платежей.",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    text = "💳 <b>История платежей</b>\n\n"
    for p in payments:
        status_emoji = "✅" if p.status.value == "succeeded" else "⏳" if p.status.value == "pending" else "❌"
        date_str = p.created_at.strftime("%d.%m.%Y")
        text += f"{status_emoji} {date_str} — {p.amount} ₽ — {p.plan}\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_features_keyboard(),
        parse_mode="HTML",
    )