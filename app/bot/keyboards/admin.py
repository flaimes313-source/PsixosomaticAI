"""
Клавиатуры для админ-панели.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# ==================== ГЛАВНОЕ МЕНЮ ====================

def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    buttons = [
        [InlineKeyboardButton(text="📋 Белый список PRO", callback_data="admin_whitelist")],
        [InlineKeyboardButton(text="📢 Создать рассылку", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📩 Обращения в поддержку", callback_data="admin_support_requests")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== РАССЫЛКА ====================

def get_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены рассылки."""
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_options_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора картинки."""
    buttons = [
        [InlineKeyboardButton(text="📨 Отправить без картинки", callback_data="broadcast_skip_image")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения рассылки."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_broadcast_recipients_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора получателей."""
    buttons = [
        [InlineKeyboardButton(text="📨 Все пользователи", callback_data="broadcast_recipients_all")],
        [InlineKeyboardButton(text="📨 Только PRO", callback_data="broadcast_recipients_pro")],
        [InlineKeyboardButton(text="📨 Только FREE", callback_data="broadcast_recipients_free")],
        [InlineKeyboardButton(text="📨 По ID (через запятую)", callback_data="broadcast_recipients_ids")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="broadcast_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ОБРАЩЕНИЯ В ПОДДЕРЖКУ ====================

def get_support_requests_list_keyboard(
    requests: list,
    page: int = 0,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:
    """
    Список обращений.
    requests — список объектов SupportRequest.
    """
    buttons = []

    for req in requests:
        date = req.created_at.strftime("%d.%m %H:%M") if req.created_at else "—"
        short = (req.message or "")[:35].replace("\n", " ").strip()
        if len(req.message or "") > 35:
            short += "..."

        status = "🟢" if not req.is_answered else "⚪"
        label = f"{status} #{req.id} · {date} · {short}"

        buttons.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"admin_support_view_{req.id}"
            )
        ])

    # Пагинация
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="⬅️ Предыдущие",
            callback_data=f"admin_support_page_{page - 1}"
        ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(
            text="➡️ Следующие",
            callback_data=f"admin_support_page_{page + 1}"
        ))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_request_view_keyboard(
    request_id: int,
    is_answered: bool,
) -> InlineKeyboardMarkup:
    """Клавиатура просмотра конкретного обращения."""
    buttons = []

    if not is_answered:
        buttons.append([
            InlineKeyboardButton(
                text="✍️ Ответить",
                callback_data=f"admin_support_reply_{request_id}"
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="✍️ Ответить снова",
                callback_data=f"admin_support_reply_{request_id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад к списку",
            callback_data="admin_support_requests"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_support_reply_cancel_keyboard(request_id: int) -> InlineKeyboardMarkup:
    """Клавиатура при вводе ответа."""
    buttons = [
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin_support_view_{request_id}"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)