"""
Обработчик для кнопки "🩺 Что я чувствую в теле".
Выбор симптома из списка → запуск психоблока.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import SymptomChoiceStates, SymptomAnalysisStates
from app.bot.keyboards.symptom_choice import (
    get_symptom_categories_keyboard,
    get_symptoms_by_category_keyboard,
    get_symptom_choice_back_keyboard,
)
from app.bot.keyboards.symptom import get_duration_keyboard
from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


# ==================== КАТЕГОРИИ СИМПТОМОВ ====================

SYMPTOM_CATEGORIES = {
    "head": ["Головная боль", "Мигрень", "Головокружение", "Давление в голове"],
    "neck_back": ["Боль в шее", "Напряжение в шее", "Боль в спине", "Боль в пояснице"],
    "chest": ["Боль в груди", "Сердцебиение", "Одышка", "Сдавленность в груди"],
    "stomach": ["Боль в животе", "Тошнота", "Изжога", "Спазмы"],
    "muscles": ["Напряжение мышц", "Боль в мышцах", "Дрожь", "Слабость"],
    "emotions": ["Тревога", "Страх", "Раздражительность", "Апатия", "Усталость"],
    "general": ["Общее недомогание", "Слабость", "Озноб", "Потливость"],
    "other": ["Другое (опишу сам)"],
}


# ==================== НОВАЯ ФУНКЦИЯ ДЛЯ ВЫЗОВА ИЗ MENU.PY ====================

async def start_symptom_choice(message: types.Message, state: FSMContext, db_session: AsyncSession = None):
    """
    Запускает сценарий 'Что я чувствую в теле'.
    Вызывается из menu.py.
    """
    await state.clear()
    await state.set_state(SymptomChoiceStates.choosing_category)
    
    await message.answer(
        "🩺 <b>Что я чувствую в теле?</b>\n\n"
        "Выбери категорию симптома:",
        reply_markup=get_symptom_categories_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User opened symptom choice: {message.from_user.id}")


# ==================== ОСНОВНОЙ ОБРАБОТЧИК ====================

@router.message(F.text == "🩺 Что я чувствую в теле")
async def show_symptom_categories(message: types.Message, state: FSMContext):
    """Показывает категории симптомов."""
    await start_symptom_choice(message, state)


@router.callback_query(SymptomChoiceStates.choosing_category, F.data.startswith("symptom_cat_"))
async def process_category_selection(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор категории и показывает список симптомов."""
    await callback.answer()
    
    category_key = callback.data.replace("symptom_cat_", "")
    category_name = {
        "head": "Головные боли",
        "neck_back": "Шея и спина",
        "chest": "Грудная клетка",
        "stomach": "Живот и ЖКТ",
        "muscles": "Мышцы и тело",
        "emotions": "Эмоции и настроение",
        "general": "Общее состояние",
        "other": "Другое",
    }.get(category_key, "Категория")
    
    symptoms = SYMPTOM_CATEGORIES.get(category_key, [])
    
    await state.update_data(category=category_key)
    await state.set_state(SymptomChoiceStates.choosing_symptom)
    
    await callback.message.edit_text(
        f"🩺 <b>{category_name}</b>\n\n"
        "Выбери конкретный симптом:",
        reply_markup=get_symptoms_by_category_keyboard(category_key, symptoms),
        parse_mode="HTML",
    )


@router.callback_query(SymptomChoiceStates.choosing_symptom, F.data.startswith("symptom_sel_"))
async def process_symptom_selection(callback: CallbackQuery, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает выбор конкретного симптома и запускает психоблок."""
    await callback.answer()
    
    symptom = callback.data.replace("symptom_sel_", "")
    
    # Если выбрано "Другое" — запрашиваем свободный ввод
    if symptom == "Другое (опишу сам)":
        await state.set_state(SymptomChoiceStates.waiting_for_custom_symptom)
        await callback.message.edit_text(
            "📝 <b>Опиши свой симптом</b>\n\n"
            "Напиши, что ты чувствуешь своими словами.\n"
            "Где именно? Какое ощущение?\n\n"
            "Например: 'тяжесть в груди', 'пульсация в висках'",
            reply_markup=get_symptom_choice_back_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # Сохраняем выбранный симптом
    await state.update_data(chosen_symptom=symptom)
    
    # Запускаем психоблок
    await start_psychoblock(callback.message, state, db_session, symptom)


@router.message(SymptomChoiceStates.waiting_for_custom_symptom, F.text)
async def process_custom_symptom(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает свободный ввод симптома."""
    symptom = message.text.strip()
    
    if len(symptom) < 3:
        await message.answer(
            "⚠️ Пожалуйста, опиши симптом подробнее (минимум 3 символа).",
            reply_markup=get_symptom_choice_back_keyboard(),
        )
        return
    
    await state.update_data(chosen_symptom=symptom)
    await start_psychoblock(message, state, db_session, symptom)


@router.message(SymptomChoiceStates.choosing_category)
async def invalid_category_input(message: types.Message, state: FSMContext):
    """Невалидный ввод при выборе категории."""
    await message.answer(
        "Пожалуйста, выбери категорию из списка ниже:",
        reply_markup=get_symptom_categories_keyboard(),
    )


@router.message(SymptomChoiceStates.choosing_symptom)
async def invalid_symptom_input(message: types.Message, state: FSMContext):
    """Невалидный ввод при выборе симптома."""
    await message.answer(
        "Пожалуйста, выбери симптом из списка ниже:",
        reply_markup=get_symptom_categories_keyboard(),
    )


@router.callback_query(F.data == "symptom_choice_back")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору категории."""
    await callback.answer()
    await state.set_state(SymptomChoiceStates.choosing_category)
    
    await callback.message.edit_text(
        "🩺 <b>Что я чувствую в теле?</b>\n\n"
        "Выбери категорию симптома:",
        reply_markup=get_symptom_categories_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "symptom_choice_cancel")
async def cancel_symptom_choice(callback: CallbackQuery, state: FSMContext):
    """Отмена выбора симптома."""
    await callback.answer("Возвращаемся в меню")
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


# ==================== ПСИХОБЛОК ====================

async def start_psychoblock(message: types.Message, state: FSMContext, db_session: AsyncSession, symptom: str):
    """
    Запускает психоблок с уточняющими вопросами.
    """
    # Используем существующую логику из symptom.py
    await state.update_data(symptom=symptom)
    await state.set_state(SymptomAnalysisStates.waiting_for_duration)
    
    await message.answer(
        f"✅ Симптом сохранён: <b>{symptom}</b>\n\n"
        "📝 Теперь ответь на несколько уточняющих вопросов.\n\n"
        "Как долго это продолжается?",
        reply_markup=get_duration_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"Psychoblock started for symptom: {symptom}")