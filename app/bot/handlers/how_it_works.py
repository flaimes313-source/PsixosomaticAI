"""
Обработчик для кнопки "Как это работает?".
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from app.bot.keyboards import get_main_menu_keyboard
from app.utils.logging import logger

router = Router()


@router.message(F.text == "📖 Как это работает?")
async def show_how_it_works(message: types.Message, state: FSMContext):
    """Показывает информацию о работе бота."""
    await state.clear()

    text = (
        "🧠 <b>Как это работает</b>\n\n"
        "📝 <b>Описать состояние</b>\n"
        "Расскажи, что сейчас происходит. Сома поможет разобраться "
        "и задаст необходимые уточняющие вопросы.\n\n"

        "📔 <b>Дневник</b>\n"
        "Здесь сохраняются твои наблюдения и диалоги с Сомой.\n\n"

        "📊 <b>Динамика</b>\n"
        "Помогает увидеть, что повторялось, что изменилось "
        "и на что может быть интересно обратить внимание.\n\n"

        "🔔 <b>Напоминания</b>\n"
        "Можно настроить утреннее напоминание, чтобы не забывать "
        "описывать своё состояние.\n\n"

        "⭐ <b>PRO</b>\n"
        "Первые 3 дня доступны бесплатно. После этого PRO позволяет "
        "общаться с Сомой без ограничений.\n\n"

        "⚠️ Сома не ставит диагнозы и не заменяет врача."
    )

    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML",
    )

    logger.info(f"User viewed 'How it works': {message.from_user.id}")