"""
Обработчик для просмотра истории анализов и уточнений.
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from zoneinfo import ZoneInfo

from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.clarification import ClarificationRepository
from app.db.models.user import User
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


def get_analysis_buttons(analyses: list, user_tz) -> InlineKeyboardMarkup:
    """Создает inline-кнопки для списка анализов."""
    buttons = []
    
    for analysis in analyses:
        symptom_preview = analysis.symptom[:30] + "..." if len(analysis.symptom) > 30 else analysis.symptom
        
        # Конвертируем время в часовой пояс пользователя
        try:
            created_at_local = analysis.created_at.astimezone(user_tz)
            date_preview = created_at_local.strftime("%d.%m")
        except:
            date_preview = analysis.created_at.strftime("%d.%m")
        
        button_text = f"🩺 {symptom_preview} ({date_preview})"
        callback_data = f"analysis_view_{analysis.id}"
        
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=callback_data
        )])
    
    buttons.append([
        InlineKeyboardButton(text="🔄 Обновить", callback_data="history_refresh"),
        InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="clear_history"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("history"))
@router.message(F.text == "📋 История")
async def show_history(message: types.Message, db_session: AsyncSession):
    """Показывает историю анализов пользователя."""
    telegram_id = message.from_user.id
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await message.answer(
                "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        # Определяем часовой пояс пользователя
        try:
            user_tz = ZoneInfo(user.timezone or "UTC")
        except:
            user_tz = ZoneInfo("UTC")
        
        # Получаем анализы
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_by_user_id(user.id, limit=10)
        
        if not analyses:
            await message.answer(
                "📋 У вас пока нет сохраненных анализов.\n\nНажмите 🧠 Разобрать симптом",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        total = await analysis_repo.get_count_by_user(user.id)
        
        history_text = (
            f"📋 Ваша история (последние {len(analyses)} из {total}):\n\n"
            "Нажмите на анализ для просмотра:"
        )
        
        keyboard = get_analysis_buttons(analyses, user_tz)
        await message.answer(history_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in show_history: {e}")
        await message.answer(
            "❌ Ошибка загрузки истории.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("analysis_view_"))
async def show_analysis_detail(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает полный анализ и уточнения."""
    await callback.answer()
    
    analysis_id = int(callback.data.split("_")[2])
    
    try:
        # Проверяем пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пожалуйста, отправьте /start",
                reply_markup=None,
            )
            return
        
        # Определяем часовой пояс пользователя
        try:
            user_tz = ZoneInfo(user.timezone or "UTC")
        except:
            user_tz = ZoneInfo("UTC")
        
        # Получаем анализ
        analysis_repo = AnalysisRepository(db_session)
        analysis = await analysis_repo.get_by_id(analysis_id)
        
        if not analysis or analysis.user_id != user.id:
            await callback.message.edit_text(
                "❌ Анализ не найден или доступ запрещен.",
                reply_markup=None,
            )
            return
        
        # Получаем уточнения для этого анализа
        clarification_repo = ClarificationRepository(db_session)
        clarifications = await clarification_repo.get_by_analysis_id(analysis_id)
        
        # Конвертируем время
        try:
            created_at_local = analysis.created_at.astimezone(user_tz)
            date = created_at_local.strftime("%d.%m.%Y %H:%M")
        except:
            date = analysis.created_at.strftime("%d.%m.%Y %H:%M")
        
        detail_text = (
            f"🧠 Полный анализ #{analysis.id}\n"
            f"📅 {date}\n\n"
            f"🩺 Симптом: {analysis.symptom}\n"
            f"⏱ Длительность: {analysis.duration}\n"
            f"📊 Интенсивность: {analysis.intensity}/10\n"
            f"📝 Контекст: {analysis.context or 'Не указан'}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"{analysis.analysis}\n\n"
        )
        
        # Добавляем уточнения, если они есть
        if clarifications:
            detail_text += (
                "━━━━━━━━━━━━━━━━━━━\n"
                f"💬 Уточняющие вопросы ({len(clarifications)}):\n\n"
            )
            for i, clar in enumerate(clarifications, 1):
                try:
                    q_date_local = clar.created_at.astimezone(user_tz)
                    q_date = q_date_local.strftime("%d.%m %H:%M")
                except:
                    q_date = clar.created_at.strftime("%d.%m %H:%M")
                
                detail_text += (
                    f"{i}. ❓ {clar.question}\n"
                    f"   📝 {clar.answer}\n"
                    f"   📅 {q_date}\n\n"
                )
        else:
            detail_text += "\n💬 Уточняющих вопросов не было.\n"
        
        detail_text += (
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ Важно: это не медицинский диагноз.\n"
            "Если симптомы беспокоят, обратитесь к врачу.\n\n"
            "🔙 Нажмите ниже, чтобы вернуться"
        )
        
        back_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="🔙 Назад к списку",
                    callback_data="back_to_history"
                )]
            ]
        )
        
        await callback.message.edit_text(
            detail_text,
            reply_markup=back_keyboard,
        )
        
    except Exception as e:
        logger.error(f"Error in show_analysis_detail: {e}")
        await callback.message.edit_text(
            "❌ Ошибка загрузки анализа.",
            reply_markup=None,
        )


# ... остальные обработчики (back_to_history, refresh_history_list, clear_history, back_to_menu) остаются без изменений