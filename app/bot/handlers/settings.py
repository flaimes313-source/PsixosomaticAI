"""
Обработчик для сценария "Настройки".
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.models.user import User
from app.db.models.analysis import Analysis
from app.db.models.clarification import Clarification
from app.bot.keyboards import get_main_menu_keyboard
from app.bot.keyboards.settings import get_settings_keyboard, get_confirm_delete_keyboard
from app.utils.logging import logger

router = Router()


@router.message(F.text == "⚙️ Настройки")
async def show_settings(message: types.Message, db_session: AsyncSession, state: FSMContext):
    """Показывает настройки пользователя."""
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
        
        # Считаем количество анализов
        result = await db_session.execute(
            select(Analysis).where(Analysis.user_id == user.id)
        )
        analyses_count = len(result.scalars().all())
        
        # Формируем профиль
        profile_text = (
            "👤 **Ваш профиль**\n\n"
            f"🆔 ID: `{user.telegram_id}`\n"
            f"👤 Имя: {user.first_name or 'Не указано'}\n"
            f"📛 Username: @{user.username or 'Не указан'}\n"
            f"🌍 Часовой пояс: {user.timezone or 'UTC (не выбран)'}\n"
            f"📊 Анализов: {analyses_count}\n"
            f"📅 Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M') if user.created_at else 'Не указано'}\n"
            f"🕐 Последний визит: {user.last_seen_at.strftime('%d.%m.%Y %H:%M') if user.last_seen_at else 'Не указано'}\n\n"
            "⚙️ **Настройки:**"
        )
        
        await message.answer(
            profile_text,
            reply_markup=get_settings_keyboard(),
            parse_mode="Markdown",
        )
        
    except Exception as e:
        logger.error(f"Error in settings: {e}")
        await message.answer(
            "❌ Произошла ошибка при загрузке настроек.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data == "back_to_menu_from_settings")
async def back_to_menu_from_settings(callback: types.CallbackQuery):
    """Возврат в главное меню."""
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "delete_all_data")
async def confirm_delete_all_data(callback: types.CallbackQuery):
    """Подтверждение удаления всех данных."""
    await callback.answer()
    
    await callback.message.edit_text(
        "⚠️ **Вы уверены, что хотите удалить все свои данные?**\n\n"
        "Это действие **нельзя отменить**.\n\n"
        "Будут удалены:\n"
        "• Ваш профиль\n"
        "• Все анализы\n"
        "• Все уточнения\n\n"
        "Ваш Telegram ID останется в системе только для технических логов.",
        reply_markup=get_confirm_delete_keyboard(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: types.CallbackQuery):
    """Отмена удаления."""
    await callback.answer()
    
    # Возвращаемся к настройкам
    await callback.message.delete()
    
    # Создаём фейковое сообщение для переиспользования
    class FakeMessage:
        def __init__(self, user_id):
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_message = FakeMessage(callback.from_user.id)
    
    from app.bot.handlers.settings import show_settings
    await show_settings(fake_message, db_session=None, state=None)


@router.callback_query(F.data == "confirm_delete_all")
async def delete_all_data(callback: types.CallbackQuery, db_session: AsyncSession):
    """Удаление всех данных пользователя."""
    await callback.answer("Удаляю данные...")
    
    telegram_id = callback.from_user.id
    
    try:
        # Находим пользователя
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await callback.message.edit_text(
                "⚠️ Пользователь не найден.",
                reply_markup=None,
            )
            return
        
        # Считаем что удаляем
        result = await db_session.execute(
            select(Analysis).where(Analysis.user_id == user.id)
        )
        analyses = result.scalars().all()
        analyses_count = len(analyses)
        
        # Удаляем все уточнения (каскадно через анализ, но на всякий случай)
        for analysis in analyses:
            await db_session.execute(
                delete(Clarification).where(Clarification.analysis_id == analysis.id)
            )
        
        # Удаляем все анализы
        await db_session.execute(
            delete(Analysis).where(Analysis.user_id == user.id)
        )
        
        # Удаляем пользователя
        await db_session.delete(user)
        await db_session.commit()
        
        await callback.message.edit_text(
            f"✅ **Все ваши данные удалены.**\n\n"
            f"Удалено:\n"
            f"• Профиль пользователя\n"
            f"• {analyses_count} анализов\n"
            f"• Все уточнения\n\n"
            "Если захотите вернуться, просто отправьте /start",
            reply_markup=None,
            parse_mode="Markdown",
        )
        
        logger.info(f"User deleted all data: telegram_id={telegram_id}, analyses={analyses_count}")
        
    except Exception as e:
        logger.error(f"Error in delete_all_data: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении данных.",
            reply_markup=None,
        )
        await callback.message.answer(
            "Главное меню:",
            reply_markup=get_main_menu_keyboard(),
        )