"""
Обработчик для раздела PRO (Сома. PRO).
Единый экран с 3 тарифами. Оплата через ЮKassa.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import get_main_menu_keyboard
from app.bot.states import ProStates
from app.services.access_service import AccessService
from app.services.payment_service import PaymentService
from app.services.yookassa_service import YooKassaService
from app.utils.logging import logger
from app.config import settings

router = Router()


# ==================== ТАРИФЫ ====================

PRO_TARIFFS = {
    "1m": {"days": 30,  "price": 490,  "label": "1 месяц"},
    "3m": {"days": 90,  "price": 1290, "label": "3 месяца"},
    "6m": {"days": 180, "price": 2290, "label": "6 месяцев"},
}


# ==================== КЛАВИАТУРЫ ====================

def get_pro_main_keyboard(is_pro: bool, with_back_to_profile: bool = False) -> InlineKeyboardMarkup:
    """
    Главная клавиатура PRO.
    Если пользователь уже PRO — только «Назад».
    Если не PRO — 3 тарифа + «Назад».
    """
    buttons = []

    if not is_pro:
        buttons.append([
            InlineKeyboardButton(
                text="⭐ 1 месяц — 490 ₽",
                callback_data="pro_buy_1m"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="⭐ 3 месяца — 1 290 ₽",
                callback_data="pro_buy_3m"
            )
        ])
        buttons.append([
            InlineKeyboardButton(
                text="⭐ 6 месяцев — 2 290 ₽",
                callback_data="pro_buy_6m"
            )
        ])

    if with_back_to_profile:
        buttons.append([
            InlineKeyboardButton(
                text="🔙 Назад в профиль",
                callback_data="pro_back_to_profile"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="pro_close"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_payment_keyboard(confirmation_url: str = None) -> InlineKeyboardMarkup:
    """Клавиатура на экране оплаты."""
    buttons = []

    if confirmation_url:
        buttons.append([
            InlineKeyboardButton(
                text="💳 Перейти к оплате",
                url=confirmation_url
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="🔄 Проверить оплату",
            callback_data="pro_check_payment"
        )
    ])
    buttons.append([
        InlineKeyboardButton(
            text="↩️ Назад",
            callback_data="pro_back"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_pro_success_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после успешной оплаты."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🌿 К диалогу",
                callback_data="survey_start_morning"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="pro_close"
            )],
        ]
    )


# ==================== ТЕКСТ ЭКРАНА PRO ====================

def _get_pro_text(is_pro: bool = False) -> str:
    """Единый текст экрана PRO."""
    text = (
        "⭐ <b>Сома PRO</b>\n\n"
        "Общайся с Сомой без ограничений.\n\n"
        "🎁 <b>Первые 3 дня PRO — бесплатно</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "🆓 <b>FREE</b>\n\n"
        "После пробных 3 дней:\n"
        "• 1 бесплатный диалог «Описать состояние»\n"
        "• до 3 уточняющих вопросов\n\n"
        "Также доступны:\n"
        "• 📔 Дневник\n"
        "• 📜 История\n"
        "• 📊 Динамика\n"
        "• 🔔 Напоминания\n"
        "• ⚙️ Настройки\n\n"
        "━━━━━━━━━━━━━━━━━━━\n\n"
        "⭐ <b>PRO</b>\n\n"
        "Всё из FREE +\n\n"
        "• ♾️ Неограниченные диалоги\n"
        "• ♾️ Неограниченные уточняющие вопросы\n\n"
        "После пробных 3 дней PRO можно продлить вручную.\n"
        "Автоматического списания нет."
    )

    if is_pro:
        text += "\n\n✅ <b>У тебя активен PRO.</b>"
    else:
        text += "\n\n━━━━━━━━━━━━━━━━━━━\n\n<b>Выбери период:</b>"

    return text


# ==================== ПОКАЗ МЕНЮ ====================

@router.message(F.text == "⭐ Сома. PRO")
async def show_pro_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню Сома. PRO (из главного меню)."""
    await state.clear()

    user_id = message.from_user.id
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)

    text = _get_pro_text(is_pro)

    await message.answer(
        text,
        reply_markup=get_pro_main_keyboard(is_pro, with_back_to_profile=False),
        parse_mode="HTML",
    )
    logger.info(f"User opened PRO menu: {user_id}")


async def show_pro_from_profile(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает Сома. PRO с возвратом в профиль."""
    await state.clear()

    user_id = message.from_user.id
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)

    text = _get_pro_text(is_pro)

    await message.answer(
        text,
        reply_markup=get_pro_main_keyboard(is_pro, with_back_to_profile=True),
        parse_mode="HTML",
    )
    logger.info(f"User opened PRO from profile: {user_id}")


# ==================== ОТКРЫТИЕ ИЗ НАПОМИНАНИЯ ====================

@router.callback_query(F.data == "pro_from_reminder")
async def show_pro_from_reminder(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Открывает PRO-меню из напоминания об окончании подписки."""
    await callback.answer()

    user_id = callback.from_user.id
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)

    text = _get_pro_text(is_pro)

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_pro_main_keyboard(is_pro, with_back_to_profile=False),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_pro_main_keyboard(is_pro, with_back_to_profile=False),
            parse_mode="HTML",
        )

    logger.info(f"User opened PRO from reminder: {user_id}")


# ==================== ОПЛАТА ====================

async def _start_payment(
    callback: CallbackQuery,
    state: FSMContext,
    db_session: AsyncSession,
    tariff_key: str,
):
    """Общая логика запуска оплаты."""
    tariff = PRO_TARIFFS.get(tariff_key)
    if not tariff:
        await callback.answer("❌ Неизвестный тариф", show_alert=True)
        return

    user_id = callback.from_user.id
    access_service = AccessService(db_session)

    if await access_service.is_pro(user_id):
        await callback.answer("У тебя уже активен PRO", show_alert=True)
        return

    await callback.answer("Создаю платёж...")

    payment_service = PaymentService(db_session, callback.bot)

    result = await payment_service.create_pro_payment(
        user_id=user_id,
        days=tariff["days"],
        amount=tariff["price"],
    )

    if not result.get("success"):
        await callback.message.edit_text(
            f"❌ Не удалось создать платёж.\n\n{result.get('error', 'Попробуйте позже.')}",
            reply_markup=get_pro_main_keyboard(False),
            parse_mode="HTML",
        )
        return

    await state.set_state(ProStates.waiting_for_payment)
    await state.update_data(payment_id=result.get("payment_id"), tariff_key=tariff_key)

    confirmation_url = result.get("confirmation_url")
    amount = result.get("amount", tariff["price"])

    text = (
        f"💳 <b>Оплата PRO</b>\n\n"
        f"Тариф: <b>{tariff['label']}</b>\n"
        f"Сумма: <b>{amount} ₽</b>\n\n"
        "Нажми на кнопку ниже, чтобы перейти к оплате.\n"
        "После оплаты PRO активируется автоматически.\n\n"
        "⏳ Ожидай подтверждения в течение нескольких минут."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_pro_payment_keyboard(confirmation_url),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_buy_1m")
async def buy_1m(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await _start_payment(callback, state, db_session, "1m")


@router.callback_query(F.data == "pro_buy_3m")
async def buy_3m(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await _start_payment(callback, state, db_session, "3m")


@router.callback_query(F.data == "pro_buy_6m")
async def buy_6m(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await _start_payment(callback, state, db_session, "6m")


# ==================== ПРОВЕРКА ОПЛАТЫ ====================

@router.callback_query(F.data == "pro_check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Проверяет статус платежа."""
    await callback.answer("Проверяю...")

    data = await state.get_data()
    payment_id = data.get("payment_id")

    if not payment_id:
        await callback.message.edit_text(
            "❌ Платёж не найден. Попробуйте начать заново.",
            reply_markup=get_pro_main_keyboard(False),
            parse_mode="HTML",
        )
        return

    payment_service = PaymentService(db_session, callback.bot)

    payment = await payment_service.payment_repo.get_by_id(payment_id, callback.from_user.id)
    if not payment:
        await callback.message.edit_text(
            "❌ Платёж не найден.",
            reply_markup=get_pro_main_keyboard(False),
            parse_mode="HTML",
        )
        return

    if payment.status == "SUCCEEDED":
        await state.clear()
        await callback.message.edit_text(
            "🎉 <b>Оплата уже подтверждена!</b>\n\n⭐ PRO активирован!",
            reply_markup=get_pro_success_keyboard(),
            parse_mode="HTML",
        )
        return

    if not payment.provider_payment_id:
        await callback.message.edit_text(
            "❌ Нет ID платежа в ЮKassa.",
            reply_markup=get_pro_main_keyboard(False),
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
                reply_markup=get_pro_main_keyboard(False),
                parse_mode="HTML",
            )
            return

    elif status == "pending":
        current_text = callback.message.text or ""
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
            reply_markup=get_pro_main_keyboard(False),
            parse_mode="HTML",
        )


# ==================== ВОЗВРАТ / ЗАКРЫТИЕ ====================

@router.callback_query(F.data == "pro_back")
async def back_to_pro_menu(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в меню PRO."""
    await callback.answer()

    user_id = callback.from_user.id
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(user_id)

    text = _get_pro_text(is_pro)

    await callback.message.edit_text(
        text,
        reply_markup=get_pro_main_keyboard(is_pro, with_back_to_profile=False),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "pro_close")
async def close_pro(callback: CallbackQuery, state: FSMContext):
    """Закрывает раздел PRO и возвращает в главное меню."""
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


@router.callback_query(F.data == "pro_back_to_profile")
async def back_to_profile_from_pro(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в профиль из PRO."""
    await callback.answer()
    await state.clear()

    from app.bot.handlers.profile import show_profile_from_callback

    try:
        await callback.message.delete()
    except Exception:
        pass

    await show_profile_from_callback(callback, state, db_session)