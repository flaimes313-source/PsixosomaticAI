"""
Обработчик для раздела PRO (Сома. PRO).
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
    get_pro_menu_keyboard_with_back_to_profile,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.bot.states import ProStates
from app.services.access_service import AccessService
from app.services.subscription_service import SubscriptionService
from app.services.payment_service import PaymentService
from app.services.yookassa_service import YooKassaService
from app.utils.logging import logger
from app.config import settings

router = Router()


# ==================== ИЗМЕНЕНО: фильтр на новое название кнопки ====================
@router.message(F.text == "⭐ Сома. PRO")
async def show_pro_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню Сома. PRO (из главного меню)."""
    await state.clear()
    
    user_id = message.from_user.id
    
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)   # нужно для клавиатуры
    
    # НОВЫЙ ТЕКСТ согласно вашему описанию
    text = (
        "⭐ <b>Сома. PRO</b>\n\n"
        "🔓 <b>Бесплатный тариф</b>\n"
        "· 1 полный разбор — уточняющие вопросы → анализ → гипотезы → рекомендации на 72 часа.\n"
        "· Анализ по 2 подходам — Синельников + современный.\n"
        "· История — 7 дней.\n"
        "· Поддержка — автоответы бота 24/7.\n\n"
        f"💎 <b>PRO — {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>\n"
        "· Безлимит разборов\n"
        "· Динамика за 30 и 90 дней\n"
        "· Неограниченный дневник\n"
        "· Расширенные отчёты\n"
        "· Напоминания под себя\n"
        "· Персонализация (запоминает паттерны)\n"
        "· Приоритетная поддержка (живой специалист по нестандартным вопросам, ответ в течение дня)\n\n"
        f"💳 {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней"
    )
    
    await message.answer(
        text,
        reply_markup=get_pro_menu_keyboard(is_pro),
        parse_mode="HTML",
    )
    logger.info(f"User opened PRO menu: {user_id}")


async def show_pro_from_profile(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает Сома. PRO с возвратом в профиль."""
    await state.clear()
    
    user_id = message.from_user.id
    
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)   # для клавиатуры
    
    # Тот же новый текст
    text = (
        "⭐ <b>Сома. PRO</b>\n\n"
        "🔓 <b>Бесплатный тариф</b>\n"
        "· 1 полный разбор — уточняющие вопросы → анализ → гипотезы → рекомендации на 72 часа.\n"
        "· Анализ по 2 подходам — Синельников + современный.\n"
        "· История — 7 дней.\n"
        "· Поддержка — автоответы бота 24/7.\n\n"
        f"💎 <b>PRO — {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>\n"
        "· Безлимит разборов\n"
        "· Динамика за 30 и 90 дней\n"
        "· Неограниченный дневник\n"
        "· Расширенные отчёты\n"
        "· Напоминания под себя\n"
        "· Персонализация (запоминает паттерны)\n"
        "· Приоритетная поддержка (живой специалист по нестандартным вопросам, ответ в течение дня)\n\n"
        f"💳 {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней"
    )
    
    await message.answer(
        text,
        reply_markup=get_pro_menu_keyboard_with_back_to_profile(is_pro),
        parse_mode="HTML",
    )
    logger.info(f"User opened PRO from profile: {user_id}")


@router.callback_query(F.data == "pro_features")
async def show_pro_features(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает подробности Сома. PRO (теперь используется тот же текст, что в меню)."""
    await callback.answer()
    
    # Для клавиатуры определяем статус (можно использовать get_pro_features_keyboard, но там может быть другая клавиатура)
    # Оставляем вызов get_pro_features_keyboard() без изменений, он, вероятно, содержит кнопку "Назад" и т.п.
    # Текст меняем на новый
    text = (
        "⭐ <b>Сома. PRO</b>\n\n"
        "🔓 <b>Бесплатный тариф</b>\n"
        "· 1 полный разбор — уточняющие вопросы → анализ → гипотезы → рекомендации на 72 часа.\n"
        "· Анализ по 2 подходам — Синельников + современный.\n"
        "· История — 7 дней.\n"
        "· Поддержка — автоответы бота 24/7.\n\n"
        f"💎 <b>PRO — {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>\n"
        "· Безлимит разборов\n"
        "· Динамика за 30 и 90 дней\n"
        "· Неограниченный дневник\n"
        "· Расширенные отчёты\n"
        "· Напоминания под себя\n"
        "· Персонализация (запоминает паттерны)\n"
        "· Приоритетная поддержка (живой специалист по нестандартным вопросам, ответ в течение дня)\n\n"
        f"💳 {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_pro_features_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_pay")
async def start_payment(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Начинает процесс оплаты Сома. PRO."""
    await callback.answer("Создаю платёж...")
    
    user_id = callback.from_user.id
    
    access_service = AccessService(db_session)
    if await access_service.is_pro(user_id):
        await callback.message.edit_text(
            "⭐ У вас уже есть PRO!\n\n"
            "Хотите продлить? Нажмите 'Продлить' в меню.",
            reply_markup=get_pro_menu_keyboard(True),
            parse_mode="HTML",
        )
        return
    
    payment_service = PaymentService(db_session, callback.bot)
    
    result = await payment_service.create_pro_payment(user_id)
    
    if not result.get("success"):
        await callback.message.edit_text(
            f"❌ Не удалось создать платёж.\n\n{result.get('error', 'Попробуйте позже.')}",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    await state.set_state(ProStates.waiting_for_payment)
    await state.update_data(payment_id=result.get("payment_id"))
    
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
    
    payment_service = PaymentService(db_session, callback.bot)
    
    payment = await payment_service.payment_repo.get_by_id(payment_id, callback.from_user.id)
    if not payment:
        await callback.message.edit_text(
            "❌ Платёж не найден.",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    if payment.status == "SUCCEEDED":
        await state.clear()
        await callback.message.edit_text(
            "🎉 <b>Оплата уже подтверждена!</b>\n\n"
            "⭐ PRO активирован!",
            reply_markup=get_pro_success_keyboard(),
            parse_mode="HTML",
        )
        return
    
    if not payment.provider_payment_id:
        await callback.message.edit_text(
            "❌ Нет ID платежа в ЮKassa.",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )
        return
    
    yookassa = YooKassaService()
    status = await yookassa.check_payment_status(payment.provider_payment_id)
    
    logger.info(f"🔄 Check payment: provider_payment_id={payment.provider_payment_id}, status={status}")
    
    if status == "succeeded":
        result = await payment_service.process_successful_webhook(
            payment.provider_payment_id,
            {}
        )
        
        if result.get("success"):
            await state.clear()
            expires_at = result.get("expires_at")
            expires_str = expires_at.strftime('%d.%m.%Y') if expires_at else "бессрочно"
            await callback.message.edit_text(
                f"🎉 <b>Оплата прошла успешно!</b>\n\n"
                f"⭐ PRO активирован!\n\n"
                f"Доступ до: <b>{expires_str}</b>",
                reply_markup=get_pro_success_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"✅ PRO activated for user {callback.from_user.id} via check_payment")
            return
        else:
            await callback.message.edit_text(
                f"⚠️ Не удалось активировать PRO. Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                reply_markup=get_pro_features_keyboard(),
                parse_mode="HTML",
            )
            return
    
    elif status == "pending":
        current_text = callback.message.text
        if "⏳" not in current_text:
            await callback.message.edit_text(
                "⏳ <b>Платёж в обработке...</b>\n\n"
                "Ожидай подтверждения. Обычно это занимает несколько минут.\n\n"
                "Нажми 'Проверить' через минуту.",
                reply_markup=get_pro_payment_keyboard(None),
                parse_mode="HTML",
            )
        else:
            await callback.answer("⏳ Платёж всё ещё в обработке. Подожди ещё немного.")
    
    else:
        await callback.message.edit_text(
            f"❌ <b>Статус платежа: {status}</b>\n\n"
            "Платёж не завершён. Попробуй ещё раз.",
            reply_markup=get_pro_features_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "pro_back")
async def back_to_pro_menu(callback: CallbackQuery, db_session: AsyncSession):
    """Возврат в меню Сома. PRO."""
    await callback.answer()
    
    user_id = callback.from_user.id
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)   # для клавиатуры
    
    # Обновлённый текст (такой же, как в основном меню)
    text = (
        "⭐ <b>Сома. PRO</b>\n\n"
        "🔓 <b>Бесплатный тариф</b>\n"
        "· 1 полный разбор — уточняющие вопросы → анализ → гипотезы → рекомендации на 72 часа.\n"
        "· Анализ по 2 подходам — Синельников + современный.\n"
        "· История — 7 дней.\n"
        "· Поддержка — автоответы бота 24/7.\n\n"
        f"💎 <b>PRO — {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней</b>\n"
        "· Безлимит разборов\n"
        "· Динамика за 30 и 90 дней\n"
        "· Неограниченный дневник\n"
        "· Расширенные отчёты\n"
        "· Напоминания под себя\n"
        "· Персонализация (запоминает паттерны)\n"
        "· Приоритетная поддержка (живой специалист по нестандартным вопросам, ответ в течение дня)\n\n"
        f"💳 {settings.PRO_PRICE_RUB} ₽ / {settings.PRO_DURATION_DAYS} дней"
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
    payment_service = PaymentService(db_session, callback.bot)
    
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


# ==================== ВОЗВРАТ В ПРОФИЛЬ ====================

@router.callback_query(F.data == "pro_back_to_profile")
async def back_to_profile_from_pro(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в профиль из PRO."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.profile import show_profile
    
    await callback.message.delete()
    await show_profile(callback.message, state, db_session)