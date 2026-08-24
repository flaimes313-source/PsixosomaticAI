"""
Клавиатуры для выбора симптомов.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_symptom_categories_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с категориями симптомов."""
    buttons = [
        [
            InlineKeyboardButton(text="🧠 Головные боли", callback_data="symptom_cat_head"),
            InlineKeyboardButton(text="🦴 Шея и спина", callback_data="symptom_cat_neck_back"),
        ],
        [
            InlineKeyboardButton(text="🫀 Грудная клетка", callback_data="symptom_cat_chest"),
            InlineKeyboardButton(text="🤢 Живот и ЖКТ", callback_data="symptom_cat_stomach"),
        ],
        [
            InlineKeyboardButton(text="💪 Мышцы и тело", callback_data="symptom_cat_muscles"),
            InlineKeyboardButton(text="😰 Эмоции", callback_data="symptom_cat_emotions"),
        ],
        [
            InlineKeyboardButton(text="🔄 Общее состояние", callback_data="symptom_cat_general"),
            InlineKeyboardButton(text="📝 Другое", callback_data="symptom_cat_other"),
        ],
        [
            InlineKeyboardButton(text="❌ Отмена", callback_data="symptom_choice_cancel"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_symptoms_by_category_keyboard(category: str, symptoms: list) -> InlineKeyboardMarkup:
    """Клавиатура с симптомами выбранной категории."""
    buttons = []
    
    for symptom in symptoms:
        # Формируем callback_data с именем симптома
        callback_data = f"symptom_sel_{symptom}"
        buttons.append([InlineKeyboardButton(text=symptom, callback_data=callback_data)])
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="🔙 Назад к категориям", callback_data="symptom_choice_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_symptom_choice_back_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Назад'."""
    buttons = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="symptom_choice_back")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="symptom_choice_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)