"""
Обработчик для кнопки «📝 Описать состояние».
Свободное описание состояния с уточняющими вопросами.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.bot.states import DescribeStateStates
from app.bot.keyboards import get_main_menu_keyboard, get_cancel_keyboard
from app.bot.keyboards.pro import get_pro_locked_keyboard
from app.services.ai_service import ai_service
from app.services.access_service import AccessService
from app.services.safety import safety_service, SafetyLevel
from app.db.models.user import User
from app.db.repositories.analysis import AnalysisRepository
from app.utils.logging import logger

router = Router()


@router.message(F.text == "📝 Описать состояние")
async def start_describe_state(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Запускает сценарий «Описать состояние».
    """
    await state.clear()
    
    telegram_id = message.from_user.id
    
    # Проверяем лимит (используем тот же, что для "Что я чувствую в теле")
    access_service = AccessService(db_session)
    can_use, limit_message = await access_service.can_use_body_analysis(telegram_id)
    
    if not can_use:
        await message.answer(
            limit_message,
            reply_markup=get_pro_locked_keyboard(),
            parse_mode="HTML",
        )
        return
    
    await state.set_state(DescribeStateStates.waiting_for_description)
    
    await message.answer(
        "📝 <b>Расскажи, как ты себя чувствуешь</b>\n\n"
        "Можешь описать тело, эмоции, мысли, сон, еду или нагрузку — что сейчас важно.\n"
        "Если не знаешь, как точно описать — просто напиши своими словами, я помогу уточнить.\n\n"
        "Например:\n"
        "• «Чувствую тяжесть в груди и тревогу»\n"
        "• «Утром болела голова, сейчас легче»\n"
        "• «Не могу сосредоточиться, всё раздражает»",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    logger.info(f"User started describe state: {telegram_id}")


@router.message(DescribeStateStates.waiting_for_description, F.text)
async def process_describe_state(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """
    Обрабатывает описание состояния и запускает AI-анализ.
    """
    telegram_id = message.from_user.id
    description = message.text.strip()
    
    if len(description) < 5:
        await message.answer(
            "⚠️ Пожалуйста, опиши состояние подробнее (минимум 5 символов).",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    # SAFETY проверка
    safety_result = safety_service.check_input(description)
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return
    
    loading_message = await message.answer(
        "🧠 Анализирую твоё состояние...\n\nПожалуйста, подожди.",
        reply_markup=get_cancel_keyboard(),
    )
    
    try:
        # Используем существующий метод анализа
        result = await ai_service.analyze_and_save(
            telegram_id=telegram_id,
            symptom=description,
            duration="Только что",
            intensity=5,
            context="Описание состояния через кнопку",
            db_session=db_session,
        )
        
        await loading_message.delete()
        
        if result["success"]:
            analysis = result["analysis"]
            analysis_id = result.get("analysis_id")
            
            # Увеличиваем счётчик
            access_service = AccessService(db_session)
            await access_service.increment_body_analysis(telegram_id)
            
            # Форматируем ответ
            from app.utils.formatter import format_analysis_for_telegram
            result_text = format_analysis_for_telegram(analysis)
            
            # Добавляем информацию о сохранении
            result_text += "\n\n✅ Сохранено в дневник и историю"
            
            # Кнопки для продолжения
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text="📝 Новое описание",
                        callback_data="describe_new"
                    )],
                    [InlineKeyboardButton(
                        text="📋 История",
                        callback_data="describe_history"
                    )],
                    [InlineKeyboardButton(
                        text="🔙 В меню",
                        callback_data="describe_back_to_menu"
                    )]
                ]
            )
            
            await state.clear()
            
            await message.answer(
                result_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
            
            logger.info(f"Describe state completed: user={telegram_id}, analysis_id={analysis_id}")
            
        else:
            await message.answer(
                f"😔 Извините, не удалось выполнить анализ.\n\n"
                f"Ошибка: {result.get('error', 'Неизвестная ошибка')}\n\n"
                "Попробуйте позже.",
                reply_markup=get_main_menu_keyboard(),
            )
            
    except Exception as e:
        await loading_message.delete()
        logger.error(f"Error in describe state: {e}")
        await message.answer(
            "😔 Произошла техническая ошибка. Попробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )


@router.message(DescribeStateStates.waiting_for_description)
async def process_describe_state_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод."""
    await message.answer(
        "Пожалуйста, опиши своё состояние текстом.",
        reply_markup=get_cancel_keyboard(),
    )


@router.callback_query(F.data == "describe_new")
async def describe_new(callback: CallbackQuery, state: FSMContext):
    """Начать новое описание."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    
    # Создаём фейковое сообщение
    class FakeMessage:
        def __init__(self, user_id):
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_message = FakeMessage(callback.from_user.id)
    await start_describe_state(fake_message, state, None)


@router.callback_query(F.data == "describe_history")
async def describe_history(callback: CallbackQuery, state: FSMContext):
    """Переход к истории."""
    await callback.answer()
    await state.clear()
    
    from app.bot.handlers.history import show_history
    await show_history(callback, db_session=None)


@router.callback_query(F.data == "describe_back_to_menu")
async def describe_back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await callback.answer()
    await state.clear()
    
    await callback.message.delete()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )