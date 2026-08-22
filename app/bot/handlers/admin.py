"""
Админские команды (только для владельца бота).
"""
import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func  # ← ДОБАВЛЕН func
from datetime import datetime  # ← ДОБАВЛЕН datetime

from app.db.models.whitelist import ProWhitelist
from app.db.models.broadcast import Broadcast
from app.db.models.user import User
from app.bot.states import AdminStates
from app.bot.keyboards.admin import (
    get_admin_menu_keyboard,
    get_broadcast_keyboard,
    get_confirm_broadcast_keyboard,
    get_broadcast_options_keyboard,
)
from app.utils.logging import logger

router = Router()

# ⚠️ УКАЖИТЕ ВАШ TELEGRAM ID
ADMIN_ID = 5997299722  # ← ЗАМЕНИТЕ НА СВОЙ


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь админом."""
    return user_id == ADMIN_ID


# ==================== ГЛАВНОЕ МЕНЮ АДМИНА ====================

@router.message(Command("admin"))
async def admin_panel(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Открывает админ-панель (только для админа)."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    await state.clear()
    await message.answer(
        "🛡️ <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"Admin opened panel: {message.from_user.id}")


@router.callback_query(F.data.startswith("admin_"))
async def admin_menu_actions(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обработка действий в админ-панели."""
    await callback.answer()
    
    action = callback.data.replace("admin_", "")
    
    if action == "back":
        await callback.message.edit_text(
            "🛡️ <b>Админ-панель</b>\n\n"
            "Выбери действие:",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    
    elif action == "whitelist":
        await show_whitelist(callback, db_session)
    
    elif action == "broadcast":
        await callback.message.edit_text(
            "📢 <b>Создать рассылку</b>\n\n"
            "Введи текст сообщения для рассылки.\n"
            "Можно отправить картинку (приложи файлом к сообщению).\n\n"
            "Чтобы отменить — нажми /cancel",
            reply_markup=get_broadcast_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(AdminStates.waiting_for_broadcast_text)
    
    elif action == "support_requests":
        await show_support_requests(callback, db_session)
    
    elif action == "stats":
        await show_stats(callback, db_session)


# ==================== БЕЛЫЙ СПИСОК ====================

async def show_whitelist(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает белый список PRO."""
    result = await db_session.execute(
        select(ProWhitelist).order_by(ProWhitelist.created_at.desc())
    )
    entries = result.scalars().all()
    
    if not entries:
        await callback.message.edit_text(
            "📋 <b>Белый список PRO</b>\n\n"
            "Список пуст.\n\n"
            "Добавить: /add_pro <Telegram ID>\n"
            "Удалить: /remove_pro <Telegram ID>",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    
    text = "📋 <b>Белый список PRO</b>\n\n"
    for entry in entries:
        user_result = await db_session.execute(
            select(User).where(User.telegram_id == entry.user_id)
        )
        user = user_result.scalar_one_or_none()
        name = user.first_name if user else "Неизвестно"
        date = entry.created_at.strftime("%d.%m.%Y")
        text += f"• <b>{entry.user_id}</b> — {name} (добавлен {date})\n"
    
    text += "\n\nДобавить: /add_pro <ID>\nУдалить: /remove_pro <ID>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("add_pro"))
async def add_pro_command(message: types.Message, db_session: AsyncSession):
    """Добавляет пользователя в белый список PRO."""
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

    # Проверяем, существует ли пользователь в БД
    result = await db_session.execute(
        select(User).where(User.telegram_id == target_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"⚠️ Пользователь с ID {target_user_id} не найден в базе.")
        return

    # Проверяем, есть ли уже в белом списке
    result = await db_session.execute(
        select(ProWhitelist).where(ProWhitelist.user_id == target_user_id)
    )
    if result.scalar_one_or_none():
        await message.answer(f"ℹ️ Пользователь {target_user_id} уже в белом списке.")
        return

    # Добавляем в белый список
    whitelist_entry = ProWhitelist(
        user_id=target_user_id,
        added_by=message.from_user.id,
    )
    db_session.add(whitelist_entry)
    await db_session.commit()

    logger.info(f"Admin {message.from_user.id} added user {target_user_id} to PRO whitelist")
    await message.answer(f"✅ Пользователь {target_user_id} добавлен в белый список PRO!")


@router.message(Command("remove_pro"))
async def remove_pro_command(message: types.Message, db_session: AsyncSession):
    """Удаляет пользователя из белого списка PRO."""
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

    result = await db_session.execute(
        select(ProWhitelist).where(ProWhitelist.user_id == target_user_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        await message.answer(f"⚠️ Пользователь {target_user_id} не найден в белом списке.")
        return

    await db_session.delete(entry)
    await db_session.commit()

    logger.info(f"Admin {message.from_user.id} removed user {target_user_id} from PRO whitelist")
    await message.answer(f"✅ Пользователь {target_user_id} удалён из белого списка PRO.")


# ==================== РАССЫЛКА ====================

@router.message(AdminStates.waiting_for_broadcast_text, F.text)
async def process_broadcast_text(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает текст для рассылки."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        await state.clear()
        return
    
    text = message.text.strip()
    
    # Сохраняем текст в FSM
    await state.update_data(broadcast_text=text)
    
    await message.answer(
        "📢 <b>Проверь сообщение</b>\n\n"
        f"Текст:\n{text}\n\n"
        "Хочешь добавить картинку? Приложи её к этому сообщению.\n"
        "Если картинка не нужна — нажми 'Отправить без картинки'.",
        reply_markup=get_broadcast_options_keyboard(),
        parse_mode="HTML",
    )
    await state.set_state(AdminStates.waiting_for_broadcast_image)


@router.message(AdminStates.waiting_for_broadcast_image, F.photo)
async def process_broadcast_image(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает картинку для рассылки."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        await state.clear()
        return
    
    # Получаем file_id картинки
    photo = message.photo[-1]
    file_id = photo.file_id
    
    await state.update_data(broadcast_image=file_id)
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)
    
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    
    await message.answer_photo(
        photo=file_id,
        caption=f"📢 <b>Проверь сообщение</b>\n\n"
                f"Текст:\n{text}\n\n"
                "Всё верно?",
        reply_markup=get_confirm_broadcast_keyboard(),
        parse_mode="HTML",
    )


@router.message(AdminStates.waiting_for_broadcast_image, F.text == "📨 Отправить без картинки")
async def send_broadcast_without_image(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Отправляет рассылку без картинки."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        await state.clear()
        return
    
    data = await state.get_data()
    text = data.get("broadcast_text", "")
    
    await state.update_data(broadcast_image=None)
    await state.set_state(AdminStates.waiting_for_broadcast_confirm)
    
    await message.answer(
        f"📢 <b>Проверь сообщение</b>\n\n"
        f"Текст:\n{text}\n\n"
        "Всё верно?",
        reply_markup=get_confirm_broadcast_keyboard(),
        parse_mode="HTML",
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
    
    # Получаем всех пользователей
    result = await db_session.execute(select(User))
    users = result.scalars().all()
    
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
    
    # Отправляем сообщения
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
            logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
            fail_count += 1
        
        # Небольшая задержка, чтобы не превысить лимиты Telegram
        await asyncio.sleep(0.05)
    
    # Обновляем статус рассылки
    broadcast.is_sent = True
    broadcast.sent_at = datetime.now()
    await db_session.commit()
    
    await state.clear()
    
    await callback.message.edit_text(
        f"✅ <b>Рассылка отправлена!</b>\n\n"
        f"Доставлено: {success_count}\n"
        f"Ошибок: {fail_count}\n"
        f"Всего: {len(users)}",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "broadcast_cancel")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки."""
    await callback.answer("Рассылка отменена")
    await state.clear()
    
    await callback.message.edit_text(
        "🛡️ <b>Админ-панель</b>\n\n"
        "Выбери действие:",
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML",
    )


# ==================== ПОДДЕРЖКА (для админа) ====================

async def show_support_requests(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает обращения в поддержку."""
    from app.db.models.support import SupportRequest
    
    result = await db_session.execute(
        select(SupportRequest)
        .where(SupportRequest.is_answered == False)
        .order_by(SupportRequest.created_at.desc())
    )
    requests = result.scalars().all()
    
    if not requests:
        await callback.message.edit_text(
            "📋 <b>Обращения в поддержку</b>\n\n"
            "Новых обращений нет.",
            reply_markup=get_admin_menu_keyboard(),
            parse_mode="HTML",
        )
        return
    
    text = "📋 <b>Обращения в поддержку</b>\n\n"
    for req in requests[:10]:
        date = req.created_at.strftime("%d.%m.%Y %H:%M")
        text += f"<b>#{req.id}</b> от {req.user_id} ({date})\n"
        text += f"📝 {req.message[:100]}...\n"
        text += f"➡️ /answer {req.id} <текст>\n\n"
    
    text += "Используйте команду /answer <ID> <текст> для ответа."
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("answer"))
async def answer_support(message: types.Message, db_session: AsyncSession):
    """Отвечает на обращение в поддержку."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    from app.db.models.support import SupportRequest
    
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
    
    # Находим обращение
    result = await db_session.execute(
        select(SupportRequest).where(SupportRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        await message.answer(f"❌ Обращение #{request_id} не найдено.")
        return
    
    # Отправляем ответ пользователю
    try:
        await message.bot.send_message(
            chat_id=request.user_id,
            text=f"📩 <b>Ответ на обращение #{request.id}</b>\n\n"
                 f"{answer_text}\n\n"
                 "━━━━━━━━━━━━━━━━━━━\n"
                 "💬 Если у вас есть ещё вопросы — напишите в поддержку.",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить ответ пользователю: {e}")
        return
    
    # Обновляем статус обращения
    request.is_answered = True
    request.answer = answer_text
    request.answered_by = message.from_user.id
    request.answered_at = datetime.now()
    await db_session.commit()
    
    await message.answer(f"✅ Ответ на обращение #{request_id} отправлен!")


# ==================== СТАТИСТИКА ====================

async def show_stats(callback: CallbackQuery, db_session: AsyncSession):
    """Показывает статистику бота."""
    from app.db.models.user import User
    from app.db.models.analysis import Analysis
    from app.db.models.diary import DiaryEntry
    from app.db.models.subscription import Subscription, PlanType
    
    # Количество пользователей
    users_result = await db_session.execute(select(User))
    users_count = len(users_result.scalars().all())
    
    # Количество анализов
    analyses_result = await db_session.execute(select(Analysis))
    analyses_count = len(analyses_result.scalars().all())
    
    # Количество записей в дневнике
    diary_result = await db_session.execute(select(DiaryEntry))
    diary_count = len(diary_result.scalars().all())
    
    # Количество PRO-пользователей
    pro_result = await db_session.execute(
        select(Subscription).where(Subscription.plan == PlanType.PRO)
    )
    pro_count = len(pro_result.scalars().all())
    
    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👤 Пользователей: <b>{users_count}</b>\n"
        f"🧠 Анализов: <b>{analyses_count}</b>\n"
        f"📔 Записей в дневнике: <b>{diary_count}</b>\n"
        f"⭐ PRO-пользователей: <b>{pro_count}</b>"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard(),
        parse_mode="HTML",
    )