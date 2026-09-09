"""
Обработчик для раздела «Моя динамика».
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
from app.services.access_service import AccessService
from app.db.models.user import User
from app.utils.logging import logger

router = Router()


@router.message(F.text == "📊 Моя динамика")
async def show_dynamics_menu(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Показывает меню выбора периода для динамики.
    """
    await state.clear()
    
    telegram_id = message.from_user.id
    
    # Проверяем доступ (PRO или FREE)
    access_service = AccessService(db_session)
    is_pro = await access_service.is_pro(telegram_id)
    
    period_text = (
        "📊 <b>Моя динамика</b>\n\n"
        "Я покажу тебе, как менялось твоё состояние за выбранный период.\n\n"
        "Выбери период:"
    )
    
    if not is_pro:
        period_text += "\n\n🔓 <b>Бесплатно:</b> 7 дней\n💎 <b>PRO:</b> 30 и 90 дней"
    
    await message.answer(
        period_text,
        reply_markup=get_dynamics_period_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(DynamicsStates.choosing_period)
    logger.info(f"User opened dynamics menu: {telegram_id}")


@router.callback_query(F.data.startswith("dynamics_period_"))
async def process_period_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """
    Обрабатывает выбор периода.
    """
    await callback.answer()
    
    period_key = callback.data.replace("dynamics_period_", "")
    telegram_id = callback.from_user.id
    access_service = AccessService(db_session)
    
    # Обработка "Свой период"
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
    
    # Проверка доступа для 30 и 90 дней
    if period_key in ["30", "90"]:
        is_pro = await access_service.is_pro(telegram_id)
        if not is_pro:
            pro_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="⭐ Подключить PRO",
                        callback_data="pro_pay"
                    )],
                    [InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="dynamics_back_to_menu"
                    )]
                ]
            )
            await callback.message.edit_text(
                "💎 <b>Динамика за 30 и 90 дней доступна только в PRO</b>\n\n"
                "В бесплатной версии доступна динамика за 7 дней.\n\n"
                "Перейди на PRO, чтобы получить расширенную аналитику!",
                reply_markup=pro_keyboard,
                parse_mode="HTML",
            )
            return
    
    period_days = int(period_key)
    await _show_dynamics_report(callback.message, state, db_session, telegram_id, period_days)


@router.message(DynamicsStates.waiting_for_custom_period, F.text)
async def process_custom_period(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обрабатывает ввод своего периода.
    """
    text = message.text.strip()
    telegram_id = message.from_user.id
    
    if text.lower() == "отмена":
        await state.clear()
        await message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        return
    
    # Пробуем распарсить как количество дней
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
    
    # Пробуем распарсить как даты
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
        await _show_dynamics_report(message, state, db_session, telegram_id, period_days, start_date, end_date)
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


async def _show_dynamics_report(
    message: types.Message,
    state: FSMContext,
    db_session: AsyncSession,
    telegram_id: int,
    period_days: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Показывает отчёт о динамике.
    """
    loading_message = await message.answer(
        "📊 <b>Анализирую динамику...</b>\n\nПожалуйста, подожди.",
        parse_mode="HTML",
    )
    
    try:
        # Получаем часовой пояс пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        user_timezone = user.timezone if user else "UTC"
        
        # Создаём сервис
        dynamics_service = DynamicsService(db_session)
        
        # Получаем отчёт
        report_result = await dynamics_service.get_report(
            user_id=telegram_id,
            period_days=period_days,
            start_date=start_date,
            end_date=end_date,
            user_timezone=user_timezone,
        )
        
        await loading_message.delete()
        
        if not report_result["success"]:
            await message.answer(
                report_result.get("message", "Не удалось получить отчёт."),
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML",
            )
            await state.clear()
            return
        
        report = report_result["report"]
        
        # Форматируем отчёт
        period_str = f"{report_result['start_date'].strftime('%d.%m.%Y')} — {report_result['end_date'].strftime('%d.%m.%Y')}"
        
        text = f"📊 <b>Динамика за {report_result['period_days']} дней</b>\n"
        text += f"📅 {period_str}\n"
        text += f"📝 {report_result['events_count']} событий\n\n"
        
        text += f"{report.get('summary', '')}\n\n"
        
        if report.get('mood_analysis'):
            text += "🎭 <b>Настроение:</b>\n"
            text += f"{report.get('mood_analysis')}\n\n"
        
        if report.get('energy_analysis'):
            text += "⚡ <b>Энергия:</b>\n"
            text += f"{report.get('energy_analysis')}\n\n"
        
        if report.get('tension_analysis'):
            text += "🧘 <b>Напряжение тела:</b>\n"
            text += f"{report.get('tension_analysis')}\n\n"
        
        if report.get('sleep_analysis'):
            text += "😴 <b>Сон:</b>\n"
            text += f"{report.get('sleep_analysis')}\n\n"
        
        if report.get('recurring_states'):
            text += "🔄 <b>Повторяющиеся состояния:</b>\n"
            for state in report.get('recurring_states', []):
                text += f"• {state}\n"
            text += "\n"
        
        if report.get('improvement_factors'):
            text += "✅ <b>Факторы улучшения:</b>\n"
            for factor in report.get('improvement_factors', []):
                text += f"• {factor}\n"
            text += "\n"
        
        if report.get('decline_factors'):
            text += "⚠️ <b>Факторы ухудшения:</b>\n"
            for factor in report.get('decline_factors', []):
                text += f"• {factor}\n"
            text += "\n"
        
        if report.get('progress'):
            text += "📈 <b>Прогресс:</b>\n"
            for item in report.get('progress', []):
                text += f"• {item}\n"
            text += "\n"
        
        if report.get('recommendations'):
            text += "🌱 <b>Рекомендации:</b>\n"
            for rec in report.get('recommendations', []):
                text += f"• {rec}\n"
            text += "\n"
        
        # Кнопки для продолжения
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="📊 Другой период",
                    callback_data="dynamics_new_period"
                )],
                [InlineKeyboardButton(
                    text="🔙 В меню",
                    callback_data="dynamics_back_to_menu"
                )]
            ]
        )
        
        await state.clear()
        
        await message.answer(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Error in dynamics report: {e}")
        await message.answer(
            "😔 Произошла ошибка при формировании отчёта. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


@router.callback_query(F.data == "dynamics_new_period")
async def dynamics_new_period(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Новый период для динамики."""
    await callback.answer()
    await callback.message.delete()
    await show_dynamics_menu(callback.message, state, db_session)


@router.callback_query(F.data == "dynamics_back_to_menu")
async def dynamics_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )