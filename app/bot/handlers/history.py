"""
Обработчик для просмотра истории сессий и уточнений.
"""
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from zoneinfo import ZoneInfo

from app.db.repositories.analysis import AnalysisRepository
from app.db.repositories.clarification import ClarificationRepository
from app.db.models.user import User
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


def get_analysis_buttons(analyses: list, user_tz) -> InlineKeyboardMarkup:
    """Создает inline-кнопки для списка сессий."""
    buttons = []
    
    for analysis in analyses:
        symptom_preview = analysis.symptom[:30] + "..." if len(analysis.symptom) > 30 else analysis.symptom
        
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
        InlineKeyboardButton(text="🔙 Назад в профиль", callback_data="back_to_profile_from_history"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("history"))
@router.message(F.text == "📋 История анализов")
async def show_history(message: types.Message, db_session: AsyncSession = None, state: FSMContext = None):
    """Показывает историю сессий пользователя."""
    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await _show_history_internal(message, new_session, state)
        return
    
    await _show_history_internal(message, db_session, state)


async def _show_history_internal(message: types.Message, db_session: AsyncSession, state: FSMContext = None):
    """Внутренняя функция для показа истории с ДЕТАЛЬНЫМ логированием."""
    if state:
        await state.clear()
    
    telegram_id = message.from_user.id
    logger.info("=" * 60)
    logger.info(f"🔍 ИЩЕМ ПОЛЬЗОВАТЕЛЯ С TELEGRAM_ID: {telegram_id}")
    
    try:
        # ============ 1. Ищем пользователя ============
        result = await db_session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(f"❌ ПОЛЬЗОВАТЕЛЬ НЕ НАЙДЕН для telegram_id: {telegram_id}")
            
            # Выведем всех пользователей из БД
            all_users = await db_session.execute(select(User))
            users_list = all_users.scalars().all()
            logger.info(f"📋 ВСЕ ПОЛЬЗОВАТЕЛИ В БД ({len(users_list)} шт.):")
            for u in users_list:
                logger.info(f"   id={u.id}, telegram_id={u.telegram_id}, name={u.first_name}")
            
            await message.answer(
                "⚠️ Вы еще не зарегистрированы.\nОтправьте /start",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        logger.info(f"✅ НАЙДЕН ПОЛЬЗОВАТЕЛЬ: id={user.id}, telegram_id={user.telegram_id}, name={user.first_name}")
        
        # ============ 2. Смотрим ВСЕ анализы в БД ============
        all_analyses_raw = await db_session.execute(
            text("SELECT id, user_id, symptom, created_at FROM analyses ORDER BY id DESC LIMIT 20")
        )
        all_analyses = all_analyses_raw.fetchall()
        logger.info(f"📊 ВСЕ АНАЛИЗЫ В БД (последние 20):")
        for a in all_analyses:
            logger.info(f"   id={a[0]}, user_id={a[1]}, symptom={a[2][:30]}..., created_at={a[3]}")
        
        # ============ 3. Получаем часовой пояс пользователя ============
        try:
            user_tz = ZoneInfo(user.timezone or "UTC")
        except:
            user_tz = ZoneInfo("UTC")
        
        # ============ 4. Ищем анализы КОНКРЕТНОГО пользователя ============
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=10)
        
        logger.info(f"🔎 АНАЛИЗЫ ДЛЯ user_id={user.id}: НАЙДЕНО {len(analyses)} шт.")
        
        if not analyses:
            # Проверим, есть ли анализы с другим user_id
            other_analyses = await db_session.execute(
                text("SELECT DISTINCT user_id FROM analyses")
            )
            other_users = other_analyses.fetchall()
            logger.info(f"👥 user_id, у которых есть анализы: {[u[0] for u in other_users]}")
            
            await message.answer(
                "📋 У вас пока нет сохраненных сессий.\n\n"
                "Нажмите 🤔 Что я чувствую в теле? или 💡 Помогите разобраться",
                reply_markup=get_main_menu_keyboard(),
            )
            return
        
        total = await analysis_repo.get_user_analyses_count(user.id)
        logger.info(f"📊 Всего анализов у пользователя: {total}")
        
        history_text = (
            f"📋 <b>История сессий</b>\n\n"
            f"Последние {len(analyses)} из {total}:\n\n"
            "Нажмите на сессию для просмотра:"
        )
        
        keyboard = get_analysis_buttons(analyses, user_tz)
        await message.answer(
            history_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"🔥 ОШИБКА в show_history: {e}")
        import traceback
        logger.error(traceback.format_exc())
        await message.answer(
            "❌ Ошибка загрузки истории.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.callback_query(F.data.startswith("analysis_view_"))
async def show_analysis_detail(callback: CallbackQuery, db_session: AsyncSession = None):
    """Показывает полную сессию и уточнения."""
    await callback.answer()
    
    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await _show_analysis_detail_internal(callback, new_session)
        return
    
    await _show_analysis_detail_internal(callback, db_session)


async def _show_analysis_detail_internal(callback: CallbackQuery, db_session: AsyncSession):
    """Внутренняя функция для показа деталей сессии."""
    analysis_id = int(callback.data.split("_")[2])
    
    try:
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
        
        try:
            user_tz = ZoneInfo(user.timezone or "UTC")
        except:
            user_tz = ZoneInfo("UTC")
        
        analysis_repo = AnalysisRepository(db_session)
        analysis = await analysis_repo.get_by_id(analysis_id)
        
        if not analysis or analysis.user_id != user.id:
            await callback.message.edit_text(
                "❌ Сессия не найдена или доступ запрещен.",
                reply_markup=None,
            )
            return
        
        clarification_repo = ClarificationRepository(db_session)
        clarifications = await clarification_repo.get_by_analysis_id(analysis_id)
        
        try:
            created_at_local = analysis.created_at.astimezone(user_tz)
            date = created_at_local.strftime("%d.%m.%Y %H:%M")
        except:
            date = analysis.created_at.strftime("%d.%m.%Y %H:%M")
        
        detail_text = (
            f"🧠 <b>Сессия #{analysis.id}</b>\n"
            f"📅 {date}\n\n"
            f"🩺 Симптом: {analysis.symptom}\n"
            f"⏱ Длительность: {analysis.duration}\n"
            f"📊 Интенсивность: {analysis.intensity}/10\n"
            f"📝 Контекст: {analysis.context or 'Не указан'}\n\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"{analysis.analysis}\n\n"
        )
        
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
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Error in show_analysis_detail: {e}")
        await callback.message.edit_text(
            "❌ Ошибка загрузки сессии.",
            reply_markup=None,
        )


@router.callback_query(F.data == "back_to_history")
async def back_to_history_list(callback: CallbackQuery, db_session: AsyncSession = None):
    """Возврат к списку сессий."""
    await callback.answer()
    
    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await _back_to_history_internal(callback, new_session)
        return
    
    await _back_to_history_internal(callback, db_session)


async def _back_to_history_internal(callback: CallbackQuery, db_session: AsyncSession):
    """Внутренняя функция для возврата к списку."""
    try:
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
        
        try:
            user_tz = ZoneInfo(user.timezone or "UTC")
        except:
            user_tz = ZoneInfo("UTC")
        
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=10)
        
        if not analyses:
            await callback.message.edit_text(
                "📋 У вас пока нет сохраненных сессий.",
                reply_markup=None,
            )
            return
        
        total = await analysis_repo.get_user_analyses_count(user.id)
        
        history_text = (
            f"📋 <b>История сессий</b>\n\n"
            f"Последние {len(analyses)} из {total}:\n\n"
            "Нажмите на сессию для просмотра:"
        )
        
        keyboard = get_analysis_buttons(analyses, user_tz)
        await callback.message.edit_text(
            history_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Error in back_to_history: {e}")
        await callback.message.edit_text(
            "❌ Ошибка загрузки истории.",
            reply_markup=None,
        )


@router.callback_query(F.data == "history_refresh")
async def refresh_history_list(callback: CallbackQuery, db_session: AsyncSession = None):
    """Обновление списка сессий."""
    await callback.answer("Обновляю...")
    
    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await _refresh_history_internal(callback, new_session)
        return
    
    await _refresh_history_internal(callback, db_session)


async def _refresh_history_internal(callback: CallbackQuery, db_session: AsyncSession):
    """Внутренняя функция для обновления списка."""
    try:
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
        
        try:
            user_tz = ZoneInfo(user.timezone or "UTC")
        except:
            user_tz = ZoneInfo("UTC")
        
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=10)
        
        if not analyses:
            await callback.message.edit_text(
                "📋 У вас пока нет сохраненных сессий.",
                reply_markup=None,
            )
            return
        
        total = await analysis_repo.get_user_analyses_count(user.id)
        
        history_text = (
            f"📋 <b>История сессий</b>\n\n"
            f"Последние {len(analyses)} из {total}:\n\n"
            "Нажмите на сессию для просмотра:"
        )
        
        keyboard = get_analysis_buttons(analyses, user_tz)
        await callback.message.edit_text(
            history_text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        
    except Exception as e:
        logger.error(f"Error in refresh_history: {e}")
        await callback.message.edit_text(
            "❌ Ошибка обновления.",
            reply_markup=None,
        )


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
        "⚠️ Вы уверены, что хотите удалить ВСЮ историю сессий?\n\n"
        "Это действие нельзя отменить. Все анализы и уточнения будут удалены.",
        reply_markup=confirm_keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "confirm_clear_history")
async def clear_history(callback: CallbackQuery, db_session: AsyncSession = None):
    """Очистка всей истории пользователя."""
    await callback.answer("Удаляю историю...")
    
    if db_session is None:
        from app.db.database import AsyncSessionLocal
        async with AsyncSessionLocal() as new_session:
            await _clear_history_internal(callback, new_session)
        return
    
    await _clear_history_internal(callback, db_session)


async def _clear_history_internal(callback: CallbackQuery, db_session: AsyncSession):
    """Внутренняя функция для очистки истории."""
    try:
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
        
        analysis_repo = AnalysisRepository(db_session)
        analyses = await analysis_repo.get_user_analyses(user.id, limit=1000)
        
        count = len(analyses)
        
        if count == 0:
            await callback.message.edit_text(
                "📋 У вас нет сессий для удаления.",
                reply_markup=None,
            )
            return
        
        for analysis in analyses:
            await db_session.delete(analysis)
        
        await db_session.commit()
        
        await callback.message.edit_text(
            f"✅ Удалено {count} сессий.\n\n"
            "Ваша история очищена.",
            reply_markup=None,
            parse_mode="HTML",
        )
        
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


@router.callback_query(F.data == "back_to_profile_from_history")
async def back_to_profile_from_history(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Возврат в профиль из истории сессий."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.profile import show_profile
    
    try:
        await callback.message.delete()
    except Exception as e:
        logger.warning(f"Could not delete message: {e}")
    
    await show_profile(callback.message, state, db_session)


@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.answer()
    
    try:
        await callback.message.edit_text(
            "Главное меню:",
            reply_markup=None,
        )
    except Exception as e:
        logger.warning(f"Could not edit message: {e}")
    
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )