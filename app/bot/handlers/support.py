"""
Обработчик раздела поддержки.

Структура:
- Меню поддержки (Частые вопросы / Задать вопрос / Назад)
- Список FAQ (6 вопросов)
- Ответы FAQ (с возвратом к вопросам)
- Механизм отправки вопроса админу (существующий)
"""
from html import escape
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import SupportStates
from app.bot.keyboards.support import (
    get_support_menu_keyboard,
    get_support_faq_keyboard,
    get_support_faq_answer_keyboard,
    get_support_cancel_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.db.models.support import SupportRequest
from app.db.models.user import User
from app.utils.logging import logger

router = Router()

# ID админа для оповещений
ADMIN_ID = 462035571


# ==================== ГЛАВНОЕ МЕНЮ ПОДДЕРЖКИ ====================

@router.message(F.text == "🆘 Поддержка")
async def show_support_menu(message: types.Message, state: FSMContext):
    """Показывает главное меню поддержки."""
    await state.clear()

    await message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Здесь можно найти ответы на частые вопросы "
        "или задать свой вопрос.",
        reply_markup=get_support_menu_keyboard(),
        parse_mode="HTML",
    )


# ==================== FAQ: СПИСОК ВОПРОСОВ ====================

@router.callback_query(F.data == "support_faq")
async def show_faq_list(callback: CallbackQuery, state: FSMContext):
    """Показывает список частых вопросов."""
    await callback.answer()
    await state.clear()

    text = (
        "❓ <b>Частые вопросы</b>\n\n"
        "Выбери вопрос:"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_support_faq_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_support_faq_keyboard(),
            parse_mode="HTML",
        )


# ==================== FAQ: ОТВЕТЫ ====================

@router.callback_query(F.data == "support_faq_about")
async def faq_about(callback: CallbackQuery):
    """Ответ: Что такое Сома и как она работает?"""
    await callback.answer()

    text = (
        "❓ <b>Что такое Сома и как она работает?</b>\n\n"
        "🌿 Сома — это AI-собеседник для наблюдения за своим состоянием.\n\n"
        "Ты рассказываешь, что замечаешь в теле, эмоциях, мыслях, сне, "
        "нагрузке или событиях жизни.\n\n"
        "Сома помогает разобраться в твоих наблюдениях и заметить "
        "возможные закономерности.\n\n"
        "Здесь не нужно искать правильные ответы или использовать "
        "психологические термины."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_support_faq_answer_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "support_faq_data")
async def faq_data(callback: CallbackQuery):
    """Ответ: Что происходит с моими данными?"""
    await callback.answer()

    text = (
        "❓ <b>Что происходит с моими данными?</b>\n\n"
        "🔐 Твои записи и диалоги сохраняются в боте, чтобы ты мог "
        "возвращаться к ним в Дневнике, Истории и Динамике.\n\n"
        "Управлять сохранёнными данными можно в разделе:\n"
        "👤 Профиль → ⚙️ Управление данными\n\n"
        "Там можно удалить все сохранённые данные.\n\n"
        "⚠️ После удаления восстановить их будет нельзя."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_support_faq_answer_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "support_faq_diagnoses")
async def faq_diagnoses(callback: CallbackQuery):
    """Ответ: Сома ставит диагнозы?"""
    await callback.answer()

    text = (
        "❓ <b>Сома ставит диагнозы?</b>\n\n"
        "Нет.\n\n"
        "Сома не ставит медицинские или психологические диагнозы "
        "и не определяет причины симптомов.\n\n"
        "Она помогает замечать собственные наблюдения и возможные "
        "закономерности.\n\n"
        "Если тебя беспокоят симптомы или состояние здоровья, "
        "обратись к врачу или другому подходящему специалисту."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_support_faq_answer_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "support_faq_pro")
async def faq_pro(callback: CallbackQuery):
    """Ответ: Что входит в PRO?"""
    await callback.answer()

    text = (
        "❓ <b>Что входит в PRO?</b>\n\n"
        "⭐ PRO позволяет общаться с Сомой без ограничений.\n\n"
        "Новым пользователям доступны первые <b>3 дня бесплатно</b>.\n\n"
        "После окончания пробного периода доступ к новым диалогам ограничен.\n\n"
        "<b>Доступны тарифы:</b>\n"
        "⭐ 1 месяц — 490 ₽\n"
        "⭐ 3 месяца — 1 290 ₽\n"
        "⭐ 6 месяцев — 2 290 ₽\n\n"
        "Подписка не продлевается автоматически."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_support_faq_answer_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "support_faq_reminders")
async def faq_reminders(callback: CallbackQuery):
    """Ответ: Как отключить утренние напоминания?"""
    await callback.answer()

    text = (
        "❓ <b>Как отключить утренние напоминания?</b>\n\n"
        "🔔 Открой:\n"
        "👤 Профиль → 🔔 Напоминания\n\n"
        "Там можно изменить время утреннего напоминания "
        "или полностью отключить его."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_support_faq_answer_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "support_faq_delete")
async def faq_delete(callback: CallbackQuery):
    """Ответ: Как удалить свои данные?"""
    await callback.answer()

    text = (
        "❓ <b>Как удалить свои данные?</b>\n\n"
        "🗑 Открой:\n"
        "👤 Профиль → ⚙️ Управление данными\n\n"
        "Выбери «Удалить все данные» и подтверди удаление.\n\n"
        "⚠️ После подтверждения восстановить удалённые данные "
        "будет нельзя."
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_support_faq_answer_keyboard(),
        parse_mode="HTML",
    )


# ==================== НАВИГАЦИЯ В FAQ ====================

@router.callback_query(F.data == "support_back_to_menu")
async def back_to_support_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню поддержки из FAQ."""
    await callback.answer()
    await state.clear()

    text = (
        "💬 <b>Поддержка</b>\n\n"
        "Здесь можно найти ответы на частые вопросы "
        "или задать свой вопрос."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_support_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_support_menu_keyboard(),
            parse_mode="HTML",
        )


@router.callback_query(F.data == "support_close")
async def close_support(callback: CallbackQuery, state: FSMContext):
    """Закрывает раздел поддержки — возврат в главное меню."""
    await callback.answer()
    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.bot.send_message(
        chat_id=callback.from_user.id,
        text="Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== «ЗАДАТЬ ВОПРОС» ====================

@router.callback_query(F.data == "support_ask")
async def start_support_question(callback: CallbackQuery, state: FSMContext):
    """Запускает ввод вопроса."""
    await callback.answer()

    text = (
        "💬 <b>Задать вопрос</b>\n\n"
        "Напиши свой вопрос ниже.\n"
        "Мы постараемся помочь."
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=get_support_cancel_keyboard(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=get_support_cancel_keyboard(),
            parse_mode="HTML",
        )

    await state.set_state(SupportStates.waiting_for_question)


@router.message(SupportStates.waiting_for_question, F.text)
async def process_support_question(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает вопрос пользователя и отправляет оповещение админу."""
    question = message.text.strip()

    if question.startswith('/'):
        return

    if len(question) < 5:
        await message.answer(
            "⚠️ Пожалуйста, напиши вопрос подробнее (минимум 5 символов).",
            reply_markup=get_support_cancel_keyboard(),
        )
        return

    # Сохраняем обращение в БД
    support_request = SupportRequest(
        user_id=message.from_user.id,
        message=question,
        is_answered=False,
    )
    db_session.add(support_request)
    await db_session.commit()

    # Сохраняем ID обращения в FSM
    await state.update_data(request_id=support_request.id)

    # ==================== АВТООТВЕТ ПОЛЬЗОВАТЕЛЮ ====================
    await message.answer(
        "✅ <b>Ваше обращение принято!</b>\n\n"
        "Мы ответим в максимально короткие сроки.\n"
        "Ответ придёт в этот чат.\n\n"
        "🆔 Номер обращения: <b>#{}</b>".format(support_request.id),
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )
    # ==============================================================

    await state.clear()

    logger.info(f"Support request created: id={support_request.id}, user={message.from_user.id}")

    # ==================== ОПОВЕЩЕНИЕ АДМИНА ====================
    try:
        user_result = await db_session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = user_result.scalar_one_or_none()
        user_name = user.first_name if user else "Неизвестно"

        safe_user_id = str(message.from_user.id)
        safe_user_name = escape(user_name)
        safe_question = escape(question)

        await message.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"📩 НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ!\n\n"
                f"🆔 #{support_request.id}\n"
                f"👤 Пользователь: {safe_user_id}\n"
                f"👤 Имя: {safe_user_name}\n"
                f"📝 Вопрос:\n{safe_question}\n\n"
                f"➡️ Ответить можно в /admin → Обращения в поддержку"
            ),
        )
        logger.info(f"✅ Admin notified about support request #{support_request.id}")
    except Exception as e:
        logger.error(f"❌ Failed to notify admin: {e}")


@router.message(SupportStates.waiting_for_question)
async def process_support_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод в поддержке."""
    await message.answer(
        "Пожалуйста, напиши свой вопрос текстом.",
        reply_markup=get_support_cancel_keyboard(),
    )


@router.callback_query(F.data == "support_cancel")
async def cancel_support(callback: CallbackQuery, state: FSMContext):
    """Отмена обращения в поддержку."""
    await callback.answer("Отменяем...")
    await state.clear()

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )