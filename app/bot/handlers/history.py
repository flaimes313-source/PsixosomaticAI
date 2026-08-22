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
@router.message(F.text == "📋 История анализов")  # ← ИСПРАВЛЕНО: точное совпадение
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
        
        # Получаем анализы — ИСПРАВЛЕНО
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=10)  # ← ИСПРАВЛЕНО
        
        if not analyses:
            await message.answer(
                "📋 У вас пока нет сохраненных анализов.\n\nНажмите 🧠 Разобрать симптом",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        total = await analysis_repo.get_user_analyses_count(user.id)  # ← ИСПРАВЛЕНО
        
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


@router.callback_query(F.data == "back_to_history")
async def back_to_history_list(callback: CallbackQuery, db_session: AsyncSession):
    """Возврат к списку анализов."""
    await callback.answer()
    
    try:
        # Находим пользователя
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
        
        # Получаем анализы
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=10)  # ← ИСПРАВЛЕНО
        
        if not analyses:
            await callback.message.edit_text(
                "📋 У вас пока нет сохраненных анализов.",
                reply_markup=None,
            )
            return
        
        total = await analysis_repo.get_user_analyses_count(user.id)  # ← ИСПРАВЛЕНО
        
        history_text = (
            f"📋 Ваша история (последние {len(analyses)} из {total}):\n\n"
            "Нажмите на анализ для просмотра:"
        )
        
        keyboard = get_analysis_buttons(analyses, user_tz)
        await callback.message.edit_text(history_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in back_to_history: {e}")
        await callback.message.edit_text(
            "❌ Ошибка загрузки истории.",
            reply_markup=None,
        )


@router.callback_query(F.data == "history_refresh")
async def refresh_history_list(callback: CallbackQuery, db_session: AsyncSession):
    """Обновление списка анализов."""
    await callback.answer("Обновляю...")
    
    try:
        # Находим пользователя
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
        
        # Получаем анализы
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=10)  # ← ИСПРАВЛЕНО
        
        if not analyses:
            await callback.message.edit_text(
                "📋 У вас пока нет сохраненных анализов.",
                reply_markup=None,
            )
            return
        
        total = await analysis_repo.get_user_analyses_count(user.id)  # ← ИСПРАВЛЕНО
        
        history_text = (
            f"📋 Ваша история (последние {len(analyses)} из {total}):\n\n"
            "Нажмите на анализ для просмотра:"
        )
        
        keyboard = get_analysis_buttons(analyses, user_tz)
        await callback.message.edit_text(history_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in refresh_history: {e}")
        await callback.message.edit_text(
            "❌ Ошибка обновления.",
            reply_markup=None,
        )


# ==================== ОЧИСТКА ИСТОРИИ ====================

@router.callback_query(F.data == "clear_history")
async def confirm_clear_history(callback: CallbackQuery):
    """Подтверждение очистки истории."""
    await callback.answer()
    
    confirm_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да, удалить все",
                    callback_data="confirm_clear_history"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="back_to_history"
                ),
            ]
        ]
    )
    
    await callback.message.edit_text(
        "⚠️ Вы уверены, что хотите удалить ВСЮ историю анализов?\n\n"
        "Это действие нельзя отменить. Все анализы и уточнения будут удалены.",
        reply_markup=confirm_keyboard,
    )


@router.callback_query(F.data == "confirm_clear_history")
async def clear_history(callback: CallbackQuery, db_session: AsyncSession):
    """Очистка всей истории пользователя."""
    await callback.answer("Удаляю историю...")
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == callback.from_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пользователь не найден.",
                reply_markup=None,
            )
            return
        
        # Получаем все анализы пользователя
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=1000)  # ← ИСПРАВЛЕНО
        
        count = len(analyses)
        
        if count == 0:
            await callback.message.edit_text(
                "📋 У вас нет анализов для удаления.",
                reply_markup=None,
            )
            return
        
        # Удаляем все анализы (уточнения удалятся каскадно)
        for analysis in analyses:
            await db_session.delete(analysis)
        
        await db_session.commit()
        
        # Показываем сообщение об успехе
        await callback.message.edit_text(
            f"✅ Удалено {count} анализов.\n\n"
            "Ваша история очищена.",
            reply_markup=None,
        )
        
        # Возвращаемся в главное меню
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
        
        logger.info(f"User cleared history: user_id={user.id}, count={count}")
        
    except Exception as e:
        logger.error(f"Error in clear_history: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при очистке истории.",
            reply_markup=None,
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "Главное меню:",
            reply_markup=None,
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in back_to_menu: {e}")
        await callback.message.delete()
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )