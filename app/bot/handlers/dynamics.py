"""
Обработчик для раздела "Моя динамика".
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import DynamicsStates
from app.bot.keyboards.dynamics import (
    get_dynamics_period_keyboard,
    get_dynamics_actions_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.schemas.dynamics import PeriodType
from app.services.dynamics_service import DynamicsService
from app.services.ai_service import AIService
from app.db.models.user import User
from app.utils.logging import logger

router = Router()


@router.message(F.text == "📊 Моя динамика")
async def show_dynamics_menu(message: types.Message, state: FSMContext):
    """Показывает меню выбора периода для динамики."""
    await state.clear()
    
    await message.answer(
        "📊 Моя динамика\n\n"
        "За какой период хочешь посмотреть динамику?\n\n"
        "🔍 Минимум для анализа — 3 записи в дневнике.",
        reply_markup=get_dynamics_period_keyboard(),
    )
    logger.info(f"User opened dynamics menu: {message.from_user.id}")


@router.callback_query(F.data.startswith("dynamics_period_"))
async def process_dynamics_period(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает выбор периода и запускает анализ."""
    await callback.answer("Анализирую...")
    
    period_type_str = callback.data.replace("dynamics_period_", "")
    period_type = PeriodType(period_type_str)
    
    telegram_id = callback.from_user.id
    
    try:
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пользователь не найден. Отправьте /start",
                reply_markup=None,
            )
            return
        
        await state.update_data(period_type=period_type)
        
        dynamics_service = DynamicsService(db_session)
        stats = await dynamics_service.calculate_statistics(user.id, period_type)
        
        if not stats:
            await callback.message.edit_text(
                "📊 Недостаточно данных для анализа динамики.\n\n"
                f"Нужно минимум 3 записи в дневнике за период.\n"
                f"Добавь ещё несколько записей в 📔 Дневник, и я смогу найти возможные закономерности.",
                reply_markup=get_dynamics_actions_keyboard(),
            )
            return
        
        await state.update_data(stats=stats)
        
        base_report = _format_basic_stats(stats)
        
        await callback.message.edit_text(
            f"{base_report}\n\n"
            "🤔 Анализирую динамику с помощью AI...",
            reply_markup=None,
        )
        
        ai_service = AIService()
        report = await ai_service.analyze_dynamics(stats)
        
        if report:
            full_report = _format_dynamics_report(stats, report)
            await callback.message.edit_text(
                full_report,
                reply_markup=get_dynamics_actions_keyboard(),
                parse_mode="HTML",
            )
            logger.info(f"Dynamics report generated for user {user.id}")
        else:
            await callback.message.edit_text(
                f"{base_report}\n\n"
                "⚠️ Сейчас не удалось сформировать AI-анализ динамики.\n"
                "Попробуй ещё раз немного позже.\n\n"
                "А пока вот базовая статистика за период:",
                reply_markup=get_dynamics_actions_keyboard(),
            )
        
    except Exception as e:
        logger.error(f"Error processing dynamics: {e}")
        await callback.message.edit_text(
            "⚠️ Не удалось выполнить анализ. Попробуй ещё раз позже.",
            reply_markup=get_dynamics_actions_keyboard(),
        )


def _format_basic_stats(stats) -> str:
    """Форматирует базовую статистику без AI."""
    days = stats.period_days
    text = (
        f"📊 Динамика за {days} дней\n"
        f"📅 {stats.start_date.strftime('%d.%m.%Y')} – {stats.end_date.strftime('%d.%m.%Y')}\n\n"
        f"📝 Записей: <b>{stats.entries_count}</b>\n"
        f"🩺 Средняя интенсивность: <b>{stats.average_intensity}/10</b>\n"
        f"   (мин: {stats.min_intensity}, макс: {stats.max_intensity})\n"
        f"😰 Средний стресс: <b>{stats.average_stress}/10</b>\n"
        f"🙂 Среднее настроение: <b>{stats.average_mood}/5</b>\n"
        f"😴 Средний сон: <b>{stats.average_sleep} ч</b>\n"
    )
    
    if stats.top_symptoms:
        text += "\n📌 Частые симптомы:\n"
        for s in stats.top_symptoms[:3]:
            text += f"• {s.symptom}: {s.count} раз, ср. интенсивность {s.average_intensity}/10\n"
    
    return text


def _format_dynamics_report(stats, report) -> str:
    """Форматирует полный отчёт с AI."""
    days = stats.period_days
    text = (
        f"📊 <b>Динамика за {days} дней</b>\n"
        f"📅 {stats.start_date.strftime('%d.%m.%Y')} – {stats.end_date.strftime('%d.%m.%Y')}\n"
        f"📝 Записей: <b>{stats.entries_count}</b>\n\n"
    )
    
    text += f"📝 <b>Общая картина</b>\n"
    text += f"{report.summary}\n\n"
    
    text += (
        f"🩺 Средняя интенсивность: <b>{stats.average_intensity}/10</b>\n"
        f"😰 Средний стресс: <b>{stats.average_stress}/10</b>\n"
        f"🙂 Среднее настроение: <b>{stats.average_mood}/5</b>\n"
        f"😴 Средний сон: <b>{stats.average_sleep} ч</b>\n\n"
    )
    
    if report.main_patterns:
        text += "🔎 <b>Что заметно</b>\n"
        for pattern in report.main_patterns[:3]:
            text += f"• {pattern}\n"
        text += "\n"
    
    if report.possible_connections:
        text += "💡 <b>Возможные связи</b>\n"
        for conn in report.possible_connections[:3]:
            text += f"• {conn}\n"
        text += "\n"
    
    if report.positive_changes:
        text += "📈 <b>Положительные изменения</b>\n"
        for change in report.positive_changes[:2]:
            text += f"• {change}\n"
        text += "\n"
    
    if report.areas_to_watch:
        text += "👀 <b>На что обратить внимание</b>\n"
        for area in report.areas_to_watch[:3]:
            text += f"• {area}\n"
        text += "\n"
    
    if report.next_steps:
        text += "💪 <b>Что можно попробовать</b>\n"
        for step in report.next_steps[:3]:
            text += f"• {step}\n"
        text += "\n"
    
    if report.medical_note:
        text += f"⚠️ {report.medical_note}\n"
    
    return text


@router.callback_query(F.data == "dynamics_back_to_menu")
async def back_to_dynamics_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню динамики."""
    await callback.answer()
    await state.clear()
    
    await callback.message.edit_text(
        "📊 Моя динамика\n\n"
        "За какой период хочешь посмотреть динамику?\n\n"
        "🔍 Минимум для анализа — 3 записи в дневнике.",
        reply_markup=get_dynamics_period_keyboard(),
    )


@router.callback_query(F.data == "dynamics_close")
async def close_dynamics(callback: CallbackQuery, state: FSMContext):
    """Закрывает динамику и возвращает в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== НОВЫЕ ОБРАБОТЧИКИ ====================

@router.callback_query(F.data == "dynamics_open_diary")
async def open_diary_from_dynamics(callback: CallbackQuery, state: FSMContext):
    """Открывает дневник из раздела динамики."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.diary import show_diary_menu
    await callback.message.delete()
    await show_diary_menu(callback.message, state)


@router.callback_query(F.data == "dynamics_new_analysis")
async def new_analysis_from_dynamics(callback: CallbackQuery, state: FSMContext):
    """Открывает новый анализ из раздела динамики."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.symptom import start_symptom_analysis
    await callback.message.delete()
    await start_symptom_analysis(callback.message, state)