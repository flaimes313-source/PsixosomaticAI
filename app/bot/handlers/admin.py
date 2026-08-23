"""
Админские команды (только для владельца бота).
"""
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func
from datetime import datetime

from app.db.models.whitelist import ProWhitelist
from app.db.models.broadcast import Broadcast
from app.db.models.support import SupportRequest
from app.db.models.user import User
from app.db.models.analysis import Analysis
from app.db.models.diary import DiaryEntry
from app.db.models.subscription import Subscription, PlanType
from app.bot.states import AdminStates
from app.bot.keyboards.admin import (
    get_admin_menu_keyboard,
    get_broadcast_keyboard,
    get_confirm_broadcast_keyboard,
    get_broadcast_options_keyboard,
    get_broadcast_recipients_keyboard,
)
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()

ADMIN_ID = 462035571


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ==================== ГЛАВНОЕ МЕНЮ ====================

@router.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext, db_session: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    await state.clear()
    await message.answer(
        "🛡️ Админ-панель\n\n"
        "Выбери действие:",
        reply_markup=get_admin_menu_keyboard(),
    )
    logger.info(f"Admin opened panel: {message.from_user.id}")


@router.callback_query(F.data.startswith("admin_"))
async def admin_menu_actions(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    await callback.answer()
    
    action = callback.data.replace("admin_", "")
    
    if action == "back":
        await callback.message.edit_text(
            "🛡️ Админ-панель\n\n"
            "Выбери действие:",
            reply_markup=get_admin_menu_keyboard(),
        )
        return
    
    elif action == "whitelist":
        await show_whitelist(callback, db_session)
    
    elif action == "broadcast":
        await callback.message.edit_text(
            "📢 Создать рассылку\n\n"
            "Выбери получателей:",
            reply_markup=get_broadcast_recipients_keyboard(),
        )
    
    elif action == "support_requests":
        await show_support_requests(callback, db_session)
    
    elif action == "stats":
        await show_stats(callback, db_session)


# ==================== ОБРАБОТЧИКИ ДЛЯ КНОПОК РАССЫЛКИ ====================

@router.callback_query(F.data.startswith("broadcast_recipients_"))
async def set_broadcast_recipients(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Выбор получателей рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.")
        return
    
    await callback.answer()
    
    recipients_type = callback.data.replace("broadcast_recipients_", "")
    
    # Сохраняем в FSM
    await state.update_data(recipients=recipients_type)
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    
    recipients_names = {
        "all": "Все пользователи",
        "pro": "Только PRO",
        "free": "Только FREE",
        "ids": "По ID",
    }
    name = recipients_names.get(recipients_type, recipients_type)
    
    await callback.message.edit_text(
        f"📢 Выбраны получатели: {name}\n\n"
        "Теперь введи текст сообщения для рассылки.\n"
        "Можно отправить картинку (приложи файлом к следующему сообщению).\n\n"
        "Чтобы отменить — нажми /cancel",
        reply_markup=None,
    )
    logger.info(f"📢 Broadcast recipients set: {recipients_type}")


@router.message(AdminStates.waiting_for_broadcast_text, F.text)
async def process_broadcast_text(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает текст для рассылки."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        await state.clear()
        return
    
    text = message.text.strip()
    await state.update_data(broadcast_text=text)
    await state.set_state(AdminStates.waiting_for_broadcast_image)
    
    await message.answer(
        f"📢 Текст получен!\n\n"
        f"Текст:\n{text}\n\n"
        "Теперь пришли картинку (если нужна) или нажми кнопку ниже, чтобы отправить без картинки.\n\n"
        "Чтобы отменить — нажми /cancel",
        reply_markup=get_broadcast_options_keyboard(),
    )
    logger.info(f"📢 Broadcast text received, length={len(text)}")


@router.message(AdminStates.waiting_for_broadcast_image, F.photo)
async def process_broadcast_image(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает картинку для рассылки."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        await state.clear()
        return
    
    photo = message.photo[-1]
    file_id = photo.file_id
    await state.update_data(broadcast_image=file_id)
    
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    recipients_type = data.get("recipients", "all")
    
    await message.answer_photo(
        photo=file_id,
        caption=f"📢 Проверь сообщение\n\n"
                f"Получатели: {recipients_type}\n"
                f"Текст:\n{text}\n\n"
                "Всё верно? Нажми кнопку ниже, чтобы отправить.",
        reply_markup=get_confirm_broadcast_keyboard(),
    )
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)


# ==================== НОВЫЙ ОБРАБОТЧИК ДЛЯ "ОТПРАВИТЬ БЕЗ КАРТИНКИ" ====================

@router.callback_query(F.data == "broadcast_skip_image")
async def skip_image_and_show_preview(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обработчик для кнопки 'Отправить без картинки'."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.")
        return
    
    await callback.answer()
    
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    recipients_type = data.get("recipients", "all")
    
    await state.update_data(broadcast_image=None)
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)
    
    await callback.message.edit_text(
        f"📢 Проверь сообщение\n\n"
        f"Получатели: {recipients_type}\n"
        f"Текст:\n{text}\n\n"
        "Всё верно? Нажми кнопку ниже, чтобы отправить.",
        reply_markup=get_confirm_broadcast_keyboard(),
    )
    logger.info(f"📢 Broadcast without image, recipients={recipients_type}")


@router.message(AdminStates.waiting_for_broadcast_image, F.text == "📨 Отправить без картинки")
async def send_broadcast_without_image_text(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Отправляет рассылку без картинки (через текст)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        await state.clear()
        return
    
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    recipients_type = data.get("recipients", "all")
    
    await state.update_data(broadcast_image=None)
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)
    
    await message.answer(
        f"📢 Проверь сообщение\n\n"
        f"Получатели: {recipients_type}\n"
        f"Текст:\n{text}\n\n"
        "Всё верно? Нажми кнопку ниже, чтобы отправить.",
        reply_markup=get_confirm_broadcast_keyboard(),
    )


@router.callback_query(F.data == "broadcast_confirm")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Подтверждение отправки рассылки."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.")
        return
    
    await callback.answer("Отправляю рассылку...")
    
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    image = data.get("broadcast_image")
    recipients_type = data.get("recipients", "all")
    
    logger.info(f"📢 FINAL: text_length={len(text)}, image={image}, recipients={recipients_type}")
    
    # Получаем пользователей
    if recipients_type == "all":
        result = await db_session.execute(select(User))
        users = result.scalars().all()
        logger.info(f"📢 All users: {len(users)}")
    elif recipients_type == "pro":
        result = await db_session.execute(
            select(User).join(ProWhitelist, User.telegram_id == ProWhitelist.user_id)
        )
        users = result.scalars().all()
        logger.info(f"📢 Pro users: {len(users)}")
    elif recipients_type == "free":
        result = await db_session.execute(
            select(User).where(
                ~User.telegram_id.in_(
                    select(ProWhitelist.user_id)
                )
            )
        )
        users = result.scalars().all()
        logger.info(f"📢 Free users: {len(users)}")
    elif recipients_type == "ids":
        # Для "По ID" нужно будет ввести ID вручную, пока пропускаем
        await callback.message.edit_text(
            "❌ Функция 'По ID' пока не реализована. Выбери другую группу.",
            reply_markup=get_broadcast_recipients_keyboard(),
        )
        return
    else:
        await callback.message.edit_text("❌ Не выбраны получатели.", reply_markup=get_admin_menu_keyboard())
        return
    
    if not users:
        await callback.message.edit_text("❌ Нет пользователей для рассылки.", reply_markup=get_admin_menu_keyboard())
        return
    
    success_count = 0
    fail_count = 0
    
    # Сохраняем рассылку в БД
    broadcast = Broadcast(
        title="Рассылка",
        message=text,
        image_url=image,
        created_by=callback.from_user.id,
        recipients_count=len(users),
    )
    db_session.add(broadcast)
    await db_session.commit()
    
    # Отправляем каждому пользователю
    for user in users:
        try:
            if image:
                await callback.bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=image,
                    caption=text,
                    parse_mode="HTML",
                )
            else:
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML",
                )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send to {user.telegram_id}: {e}")
            fail_count += 1
        await asyncio.sleep(0.05)
    
    broadcast.is_sent = True
    broadcast.sent_at = datetime.now()
    await db_session.commit()
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ Рассылка отправлена!\n\n"
        f"Доставлено: {success_count}\n"
        f"Ошибок: {fail_count}\n"
        f"Всего: {len(users)}",
        reply_markup=get_admin_menu_keyboard(),
    )


@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки."""
    await callback.answer("Рассылка отменена")
    await state.clear()
    await callback.message.edit_text(
        "🛡️ Админ-панель\n\n"
        "Выбери действие:",
        reply_markup=get_admin_menu_keyboard(),
    )


# ==================== БЕЛЫЙ СПИСОК ====================

async def show_whitelist(callback: CallbackQuery, db_session: AsyncSession):
    try:
        result = await db_session.execute(
            select(ProWhitelist).order_by(ProWhitelist.created_at.desc())
        )
        entries = result.scalars().all()
        
        if not entries:
            await callback.message.edit_text(
                "📋 Белый список PRO\n\n"
                "Список пуст.\n\n"
                "Добавить: /add_pro <Telegram ID>\n"
                "Удалить: /remove_pro <Telegram ID>",
                reply_markup=get_admin_menu_keyboard(),
            )
            return
        
        text = "📋 Белый список PRO\n\n"
        for entry in entries:
            user_result = await db_session.execute(
                select(User).where(User.telegram_id == entry.user_id)
            )
            user = user_result.scalar_one_or_none()
            name = user.first_name if user else "Неизвестно"
            date = entry.created_at.strftime("%d.%m.%Y")
            text += f"• {entry.user_id} — {name} (добавлен {date})\n"
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in show_whitelist: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при загрузке белого списка.",
            reply_markup=get_admin_menu_keyboard(),
        )


@router.message(Command("add_pro"))
async def add_pro_command(message: types.Message, db_session: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Используйте: /add_pro <Telegram ID>\n"
            "Например: /add_pro 123456789"
        )
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    try:
        result = await db_session.execute(
            select(User).where(User.telegram_id == target_user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer(f"⚠️ Пользователь с ID {target_user_id} не найден в базе.")
            return

        result = await db_session.execute(
            select(ProWhitelist).where(ProWhitelist.user_id == target_user_id)
        )
        if result.scalar_one_or_none():
            await message.answer(f"ℹ️ Пользователь {target_user_id} уже в белом списке.")
            return

        whitelist_entry = ProWhitelist(
            user_id=target_user_id,
            added_by=message.from_user.id,
        )
        db_session.add(whitelist_entry)
        await db_session.commit()

        logger.info(f"Admin added user {target_user_id} to PRO whitelist")
        await message.answer(f"✅ Пользователь {target_user_id} добавлен в белый список PRO!")
    except Exception as e:
        logger.error(f"Error in add_pro: {e}")
        await message.answer("❌ Ошибка при добавлении пользователя.")


@router.message(Command("remove_pro"))
async def remove_pro_command(message: types.Message, db_session: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Используйте: /remove_pro <Telegram ID>\n"
            "Например: /remove_pro 123456789"
        )
        return

    try:
        target_user_id = int(args[1])
    except ValueError:
        await message.answer("❌ Telegram ID должен быть числом.")
        return

    try:
        result = await db_session.execute(
            select(ProWhitelist).where(ProWhitelist.user_id == target_user_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            await message.answer(f"⚠️ Пользователь {target_user_id} не найден в белом списке.")
            return

        await db_session.delete(entry)
        await db_session.commit()

        logger.info(f"Admin removed user {target_user_id} from PRO whitelist")
        await message.answer(f"✅ Пользователь {target_user_id} удалён из белого списка PRO.")
    except Exception as e:
        logger.error(f"Error in remove_pro: {e}")
        await message.answer("❌ Ошибка при удалении пользователя.")


# ==================== ПОДДЕРЖКА ====================

async def show_support_requests(callback: CallbackQuery, db_session: AsyncSession):
    try:
        result = await db_session.execute(
            select(SupportRequest)
            .where(SupportRequest.is_answered == False)
            .order_by(SupportRequest.created_at.desc())
        )
        requests = result.scalars().all()
        
        if not requests:
            await callback.message.edit_text(
                "📋 Обращения в поддержку\n\n"
                "Новых обращений нет.",
                reply_markup=get_admin_menu_keyboard(),
            )
            return
        
        text = "📋 Обращения в поддержку\n\n"
        for req in requests[:10]:
            date = req.created_at.strftime("%d.%m.%Y %H:%M")
            text += f"#{req.id} от {req.user_id} ({date})\n"
            text += f"📝 {req.message[:100]}...\n"
            text += f"➡️ /answer {req.id} <текст>\n\n"
        
        text += "Используйте команду /answer <ID> <текст> для ответа."
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in show_support_requests: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при загрузке обращений.",
            reply_markup=get_admin_menu_keyboard(),
        )


@router.message(Command("answer"))
async def answer_support(message: types.Message, db_session: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Используйте: /answer <ID> <текст ответа>\n"
            "Например: /answer 5 Спасибо за обращение!"
        )
        return

    try:
        request_id = int(args[1])
        answer_text = args[2]
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    try:
        result = await db_session.execute(
            select(SupportRequest).where(SupportRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        if not request:
            await message.answer(f"❌ Обращение #{request_id} не найдено.")
            return

        await message.bot.send_message(
            chat_id=request.user_id,
            text=f"📩 Ответ на обращение #{request.id}\n\n"
                 f"{answer_text}\n\n"
                 "━━━━━━━━━━━━━━━━━━━\n"
                 "💬 Если у вас есть ещё вопросы — напишите в поддержку.",
            parse_mode="HTML",
        )

        request.is_answered = True
        request.answer = answer_text
        request.answered_by = message.from_user.id
        request.answered_at = datetime.now()
        await db_session.commit()

        await message.answer(f"✅ Ответ на обращение #{request_id} отправлен!")
    except Exception as e:
        logger.error(f"Error in answer_support: {e}")
        await message.answer(f"❌ Ошибка при ответе: {e}")


# ==================== СТАТИСТИКА ====================

async def show_stats(callback: CallbackQuery, db_session: AsyncSession):
    try:
        users_count = (await db_session.execute(select(func.count()).select_from(User))).scalar()
        analyses_count = (await db_session.execute(select(func.count()).select_from(Analysis))).scalar()
        diary_count = (await db_session.execute(select(func.count()).select_from(DiaryEntry))).scalar()
        pro_count = (await db_session.execute(
            select(func.count()).select_from(Subscription).where(Subscription.plan == PlanType.PRO)
        )).scalar()
        
        text = (
            f"📊 Статистика бота\n\n"
            f"👤 Пользователей: {users_count or 0}\n"
            f"🧠 Анализов: {analyses_count or 0}\n"
            f"📔 Записей в дневнике: {diary_count or 0}\n"
            f"⭐ PRO-пользователей: {pro_count or 0}"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_admin_menu_keyboard(),
        )
    except Exception as e:
        logger.error(f"Error in show_stats: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при загрузке статистики.",
            reply_markup=get_admin_menu_keyboard(),
        )