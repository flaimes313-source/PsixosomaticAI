"""
Обработчик для раздела «Моя динамика».

Логика:
- Периоды: 3, 7, 14, 30, 90 дней + «Свой период»
- Динамика доступна всем (FREE, PRO, trial) — безлимит
- Отчёт — обычный текст (не JSON)
- Заглушки:
  * 0 записей → «Пока нечего анализировать» + [📝 Описать состояние]
  * 1-2 записи → «Пока наблюдений немного» + [↩️ Назад]
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, date
from typing import Optional

from app.bot.states import DynamicsStates
from app.bot.keyboards.dynamics import (
    get_dynamics_period_keyboard,
    get_dynamics_cancel_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.services.dynamics_service import DynamicsService
from app.db.models.user import User
from app.utils.logging import logger

router = Router()


# ==================== КЛАВИАТУРЫ ДЛЯ ЗАГЛУШЕК ====================

def get_empty_dynamics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для заглушки «нет записей»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📝 Описать состояние",
                callback_data="survey_start_morning"
            )],
            [InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="dynamics_back_to_menu"
            )],
        ]
    )


def get_too_few_dynamics_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для заглушки «мало записей»."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="↩️ Назад",
                callback_data="dynamics_back_to_menu"
            )],
        ]
    )


def get_dynamics_report_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после обычного отчёта."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📊 Другой период",
                callback_data="dynamics_new_period"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="dynamics_back_to_menu"
            )],
        ]
    )


# ==================== МЕНЮ ВЫБОРА ПЕРИОДА ====================

@router.message(F.text == "📊 Моя динамика")
async def show_dynamics_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Показывает меню выбора периода для динамики."""
    await state.clear()

    telegram_id = message.from_user.id

    period_text = (
        "📊 <b>Моя динамика</b>\n\n"
        "Я покажу тебе, как менялось твоё состояние за выбранный период.\n\n"
        "Выбери период:"
    )

    await message.answer(
        period_text,
        reply_markup=get_dynamics_period_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(DynamicsStates.choosing_period)
    logger.info(f"User opened dynamics menu: {telegram_id}")


# ==================== ВЫБОР ПЕРИОДА ====================

@router.callback_query(F.data.startswith("dynamics_period_"))
async def process_period_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает выбор периода."""
    await callback.answer()

    period_key = callback.data.replace("dynamics_period_", "")
    telegram_id = callback.from_user.id

    if period_key == "custom":
        await callback.message.edit_text(
            "📝 <b>Введи свой период</b>\n\n"
            "Напиши количество дней (например: 5, 14, 21)\n"
            "Или укажи даты в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ\n"
            "Например: 01.09.2026-07.09.2026\n\n"
            "Напиши 'Отмена', чтобы выйти.",
            reply_markup=None,
        )
        await state.set_state(DynamicsStates.waiting_for_custom_period)
        return

    # Все периоды доступны всем — без проверки PRO
    try:
        period_days = int(period_key)
    except ValueError:
        await callback.message.edit_text(
            "⚠️ Неверный период.",
            reply_markup=get_dynamics_period_keyboard(),
        )
        return

    await _show_dynamics_report(callback.message, state, db_session, telegram_id, period_days)


# ==================== СВОЙ ПЕРИОД ====================

@router.message(DynamicsStates.waiting_for_custom_period, F.text)
async def process_custom_period(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает ввод своего периода."""
    text = message.text.strip()
    telegram_id = message.from_user.id

    if text.lower() == "отмена":
        await state.clear()
        await message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    # Попытка 1: число дней
    try:
        period_days = int(text)
        if period_days < 1 or period_days > 365:
            await message.answer(
                "⚠️ Пожалуйста, укажи количество дней от 1 до 365.",
                reply_markup=get_dynamics_cancel_keyboard(),
            )
            return
        await _show_dynamics_report(message, state, db_session, telegram_id, period_days)
        return
    except ValueError:
        pass

    # Попытка 2: диапазон дат
    try:
        parts = text.split("-")
        if len(parts) != 2:
            raise ValueError

        start_date = datetime.strptime(parts[0].strip(), "%d.%m.%Y").date()
        end_date = datetime.strptime(parts[1].strip(), "%d.%m.%Y").date()

        if start_date > end_date:
            await message.answer(
                "⚠️ Начальная дата не может быть позже конечной.",
                reply_markup=get_dynamics_cancel_keyboard(),
            )
            return

        period_days = (end_date - start_date).days + 1
        await _show_dynamics_report(
            message, state, db_session, telegram_id, period_days, start_date, end_date
        )
        return
    except ValueError:
        await message.answer(
            "⚠️ Неверный формат.\n\n"
            "Напиши количество дней (например: 14)\n"
            "Или даты в формате: 01.09.2026-07.09.2026",
            reply_markup=get_dynamics_cancel_keyboard(),
        )
        return


@router.message(DynamicsStates.waiting_for_custom_period)
async def process_custom_period_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод."""
    await message.answer(
        "Пожалуйста, введи количество дней или даты в формате ДД.ММ.ГГГГ-ДД.ММ.ГГГГ",
        reply_markup=get_dynamics_cancel_keyboard(),
    )


# ==================== ОТЧЁТ ====================

async def _show_dynamics_report(
    message: types.Message,
    state: FSMContext,
    db_session: AsyncSession,
    telegram_id: int,
    period_days: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Показывает отчёт о динамике."""
    loading_message = await message.answer(
        "📊 <b>Анализирую динамику...</b>\n\nПожалуйста, подожди.",
        parse_mode="HTML",
    )

    try:
        # Получаем user.id
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            try:
                await loading_message.delete()
            except Exception:
                pass
            await message.answer(
                "⚠️ Пользователь не найден. Отправьте /start",
                reply_markup=get_main_menu_keyboard(),
            )
            await state.clear()
            return

        user_id = user.id
        user_timezone = user.timezone if user else "UTC"

        dynamics_service = DynamicsService(db_session)

        report_result = await dynamics_service.get_report(
            user_id=user_id,
            period_days=period_days,
            start_date=start_date,
            end_date=end_date,
            user_timezone=user_timezone,
        )

        try:
            await loading_message.delete()
        except Exception:
            pass

        # ==================== ЗАГЛУШКА: НЕТ ЗАПИСЕЙ ====================
        if report_result.get("is_empty"):
            await state.clear()
            await message.answer(
                report_result["report_text"],
                reply_markup=get_empty_dynamics_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"Dynamics empty for user {telegram_id}")
            return

        # ==================== ЗАГЛУШКА: МАЛО ЗАПИСЕЙ ====================
        if report_result.get("is_too_few"):
            await state.clear()
            await message.answer(
                report_result["report_text"],
                reply_markup=get_too_few_dynamics_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"Dynamics too few events for user {telegram_id}")
            return

        # ==================== ОБЫЧНЫЙ ОТЧЁТ ====================
        if not report_result.get("success"):
            await message.answer(
                report_result.get("message", "Не удалось получить отчёт."),
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML",
            )
            await state.clear()
            return

        # Формируем финальный текст: заголовок с периодом + текст от AI
        period_str = (
            f"{report_result['start_date'].strftime('%d.%m.%Y')} — "
            f"{report_result['end_date'].strftime('%d.%m.%Y')}"
        )

        text = (
            f"📊 <b>Динамика за {report_result['period_days']} дней</b>\n"
            f"📅 {period_str}\n"
            f"📝 {report_result['events_count']} записей\n\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"{report_result['report_text']}"
        )

        await state.clear()

        await message.answer(
            text,
            reply_markup=get_dynamics_report_keyboard(),
            parse_mode="HTML",
        )

        logger.info(f"Dynamics report sent to user {telegram_id}")

    except Exception as e:
        try:
            await loading_message.delete()
        except Exception:
            pass
        logger.error(f"Error in dynamics report: {e}", exc_info=True)
        await message.answer(
            "😔 Произошла ошибка при формировании отчёта. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


# ==================== КНОПКИ ДЕЙСТВИЙ ====================

@router.callback_query(F.data == "dynamics_new_period")
async def dynamics_new_period(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Новый период для динамики."""
    await callback.answer()
    try:
        await callback.message.delete()
    except Exception:
        pass
    await show_dynamics_menu(callback.message, state, db_session)


@router.callback_query(F.data == "dynamics_back_to_menu")
async def dynamics_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
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