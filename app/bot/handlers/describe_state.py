"""
Обработчик для кнопки «📝 Описать состояние».
Полноценный диалог с живым AI-ответом (без JSON, без шаблонов).
Сохраняет всё в DiaryEvent.
"""
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from app.bot.states import DescribeStateStates
from app.bot.keyboards import get_main_menu_keyboard, get_cancel_keyboard
from app.bot.keyboards.pro import get_pro_locked_keyboard
from app.services.ai_service import ai_service
from app.services.access_service import AccessService
from app.services.diary_event_service import DiaryEventService
from app.services.safety import safety_service, SafetyLevel
from app.db.models.user import User
from app.db.repositories.clarification import ClarificationRepository
from app.utils.logging import logger

router = Router()


@router.message(F.text == "📝 Описать состояние")
async def start_describe_state(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Запускает сценарий «Описать состояние»."""
    await state.clear()
    
    telegram_id = message.from_user.id
    
    access_service = AccessService(db_session)
    can_use, limit_message = await access_service.can_use_body_analysis(telegram_id)
    
    if not can_use:
        await message.answer(
            limit_message,
            reply_markup=get_pro_locked_keyboard(),
            parse_mode="HTML",
        )
        return
    
    # Создаём сессию
    session_id = str(uuid.uuid4())
    
    await state.update_data(
        session_id=session_id,
        dialog_history=[],
        is_first_message=True,
    )
    await state.set_state(DescribeStateStates.waiting_for_description)
    
    dialog_message = await message.answer(
        "📝 <b>Расскажи, как ты себя чувствуешь</b>\n\n"
        "Можешь описать тело, эмоции, мысли, сон, еду или нагрузку — что сейчас важно.\n"
        "Если не знаешь, как точно описать — просто напиши своими словами, я помогу уточнить.\n\n"
        "Например:\n"
        "• «Чувствую тяжесть в груди и тревогу»\n"
        "• «Утром болела голова, сейчас легче»\n"
        "• «Не могу сосредоточиться, всё раздражает»\n\n"
        "Я отвечу естественно, без шаблонов — как в живом разговоре.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML",
    )
    
    await state.update_data(dialog_message_id=dialog_message.message_id)
    logger.info(f"User started describe state: {telegram_id}, session={session_id}")


@router.message(DescribeStateStates.waiting_for_description, F.text)
async def process_describe_state(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Обрабатывает первое описание состояния."""
    telegram_id = message.from_user.id
    description = message.text.strip()
    
    if len(description) < 5:
        await message.answer(
            "⚠️ Пожалуйста, опиши состояние подробнее (минимум 5 символов).",
            reply_markup=get_cancel_keyboard(),
        )
        return
    
    safety_result = safety_service.check_input(description)
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return
    
    data = await state.get_data()
    dialog_message_id = data.get("dialog_message_id")
    session_id = data.get("session_id")
    
    diary_service = DiaryEventService(db_session)
    
    # ==================== СОХРАНЯЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ ====================
    await diary_service.record_user_message(
        user_id=telegram_id,
        content=description,
        session_id=session_id,
        source="describe_state",
    )
    # =========================================================================
    
    loading_message = await message.answer(
        "🧠 <b>Думаю над твоим состоянием...</b>\n\nПожалуйста, подожди.",
        parse_mode="HTML",
    )
    
    try:
        result = await ai_service.describe_state(
            description=description,
            telegram_id=telegram_id,
            db_session=db_session,
        )
        
        try:
            await loading_message.delete()
        except Exception:
            pass
        
        if result["success"]:
            answer = result["answer"]
            analysis_id = result.get("analysis_id")
            
            access_service = AccessService(db_session)
            await access_service.increment_body_analysis(telegram_id)
            
            # ==================== СОХРАНЯЕМ ОТВЕТ AI ====================
            await diary_service.record_ai_response(
                user_id=telegram_id,
                content=answer,
                session_id=session_id,
                source="describe_state",
                analysis_id=analysis_id,
            )
            # =============================================================
            
            dialog_text = f"📝 <b>Ты написал:</b>\n{description}\n\n"
            dialog_text += f"🧠 <b>Я думаю:</b>\n{answer}\n\n"
            dialog_text += "✅ Сохранено в дневник и историю\n\n"
            dialog_text += "━━━━━━━━━━━━━━━━━━━\n\n"
            dialog_text += "💬 <b>Продолжим диалог?</b>\nНапиши следующий вопрос или уточнение."
            
            await state.update_data(
                analysis_id=analysis_id,
                is_dialog_active=True,
                dialog_history=[
                    {"role": "user", "content": description},
                    {"role": "assistant", "content": answer}
                ],
                dialog_text=dialog_text,
                dialog_message_id=dialog_message_id,
            )
            await state.set_state(DescribeStateStates.waiting_for_continue)
            
            try:
                await message.edit_text(
                    text=dialog_text,
                    reply_markup=get_continue_dialog_keyboard(),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.error(f"Error editing message: {e}")
                await message.answer(
                    dialog_text,
                    reply_markup=get_continue_dialog_keyboard(),
                    parse_mode="HTML",
                )
            
            try:
                await message.delete()
            except Exception:
                pass
            
            logger.info(f"Describe state completed: user={telegram_id}")
            
        else:
            await message.answer(
                f"😔 Извините, не удалось выполнить анализ.\n\n"
                f"Ошибка: {result.get('error', 'Попробуйте позже.')}",
                reply_markup=get_main_menu_keyboard(),
            )
            await state.clear()
            
    except Exception as e:
        try:
            await loading_message.delete()
        except Exception:
            pass
        logger.error(f"Error in describe state: {e}")
        await message.answer(
            "😔 Произошла техническая ошибка. Попробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()


# ==================== ПРОДОЛЖЕНИЕ ДИАЛОГА ====================

@router.message(DescribeStateStates.waiting_for_continue, F.text)
async def continue_describe_dialog(message: types.Message, state: FSMContext, db_session: AsyncSession):
    """Продолжает диалог."""
    telegram_id = message.from_user.id
    user_text = message.text.strip()
    
    if len(user_text) < 3:
        await message.answer(
            "Пожалуйста, напиши более развёрнутое сообщение (минимум 3 символа).",
        )
        return
    
    safety_result = safety_service.check_input(user_text)
    if safety_result.level == SafetyLevel.CRITICAL:
        await message.answer(
            safety_result.warning or "⚠️ Обнаружены симптомы, требующие медицинского внимания.",
            reply_markup=get_main_menu_keyboard(),
        )
        await state.clear()
        return
    
    data = await state.get_data()
    session_id = data.get("session_id")
    analysis_id = data.get("analysis_id")
    dialog_history = data.get("dialog_history", [])
    dialog_text = data.get("dialog_text", "")
    dialog_message_id = data.get("dialog_message_id")
    
    dialog_history.append({"role": "user", "content": user_text})
    
    diary_service = DiaryEventService(db_session)
    
    # ==================== СОХРАНЯЕМ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ ====================
    await diary_service.record_user_message(
        user_id=telegram_id,
        content=user_text,
        session_id=session_id,
        source="describe_state",
    )
    # =========================================================================
    
    loading_message = await message.answer(
        "🧠 <b>Думаю...</b>\n\nПожалуйста, подожди.",
        parse_mode="HTML",
    )
    
    try:
        context = ""
        for msg in dialog_history:
            role = "Пользователь" if msg.get("role") == "user" else "Ты (AI)"
            context += f"{role}: {msg.get('content')}\n"
        
        from app.services.yandex_gpt import YandexGPTClient
        
        system_prompt = """
Ты — AI-помощник «Сома. Забота о себе.»

Вы продолжаете диалог. Пользователь уже описал своё состояние, и ты ответил.

Теперь пользователь задаёт новый вопрос или уточнение.

Отвечай естественно, как в живом разговоре. Учитывай предыдущий диалог.

Ты не врач, не психотерапевт и не ставишь диагнозов.
Твоя задача — бережное сопровождение и поддержка.

Не используй JSON. Не используй шаблоны.
Будь дружелюбным, тёплым, поддерживающим.
"""
        
        user_prompt = f"""
ИСТОРИЯ ДИАЛОГА

{context}

ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ

{user_text}

Ответь естественно, как в живом разговоре. Учитывай предыдущий диалог.
"""
        
        client = YandexGPTClient()
        response = await client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=3000,
        )
        
        try:
            await loading_message.delete()
        except Exception:
            pass
        
        dialog_history.append({"role": "assistant", "content": response})
        
        # ==================== СОХРАНЯЕМ ОТВЕТ AI ====================
        await diary_service.record_ai_response(
            user_id=telegram_id,
            content=response,
            session_id=session_id,
            source="describe_state",
            analysis_id=analysis_id,
        )
        # =============================================================
        
        # Сохраняем уточнение в Clarification (для обратной совместимости)
        try:
            if analysis_id:
                user_result = await db_session.execute(
                    select(User).where(User.telegram_id == telegram_id)
                )
                user = user_result.scalar_one_or_none()
                
                if user:
                    clarification_repo = ClarificationRepository(db_session)
                    await clarification_repo.create(
                        analysis_id=analysis_id,
                        user_id=user.id,
                        question=user_text,
                        answer=response,
                    )
        except Exception as e:
            logger.error(f"Failed to save clarification: {e}")
        
        last_messages = dialog_history[-10:] if len(dialog_history) > 10 else dialog_history
        
        new_dialog_text = "📝 <b>Твой диалог с AI</b>\n\n"
        for msg in last_messages:
            if msg.get("role") == "user":
                new_dialog_text += f"👤 <b>Ты:</b> {msg.get('content')}\n\n"
            else:
                new_dialog_text += f"🧠 <b>Я:</b> {msg.get('content')}\n\n"
        
        new_dialog_text += "━━━━━━━━━━━━━━━━━━━\n\n"
        new_dialog_text += "💬 <b>Продолжим?</b>\nНапиши следующий вопрос или уточнение."
        
        await state.update_data(
            dialog_history=dialog_history,
            dialog_text=new_dialog_text,
        )
        
        try:
            await message.edit_text(
                text=new_dialog_text,
                reply_markup=get_continue_dialog_keyboard(),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            await message.answer(
                new_dialog_text,
                reply_markup=get_continue_dialog_keyboard(),
                parse_mode="HTML",
            )
        
        try:
            await message.delete()
        except Exception:
            pass
        
    except Exception as e:
        try:
            await loading_message.delete()
        except Exception:
            pass
        logger.error(f"Error in continue dialog: {e}")
        await message.answer(
            "😔 Произошла ошибка. Попробуйте ещё раз.",
            reply_markup=get_continue_dialog_keyboard(),
        )


@router.message(DescribeStateStates.waiting_for_continue)
async def continue_dialog_invalid(message: types.Message, state: FSMContext):
    """Невалидный ввод при продолжении диалога."""
    await message.answer(
        "Пожалуйста, напиши текстовое сообщение.",
    )


@router.callback_query(F.data == "describe_finish")
async def describe_finish(callback: CallbackQuery, state: FSMContext):
    """Завершение диалога."""
    await callback.answer("Диалог завершён")
    
    data = await state.get_data()
    dialog_message_id = data.get("dialog_message_id")
    dialog_text = data.get("dialog_text", "")
    
    final_text = dialog_text + "\n\n✅ <b>Диалог завершён</b>\nСпасибо, что поделились! 🙏"
    
    try:
        await callback.message.edit_text(
            text=final_text,
            reply_markup=None,
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.answer(
            final_text,
            reply_markup=None,
            parse_mode="HTML",
        )
    
    await state.clear()
    
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard(),
    )


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


# ==================== КЛАВИАТУРА ДЛЯ ПРОДОЛЖЕНИЯ ====================

def get_continue_dialog_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для продолжения диалога."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="✅ Завершить диалог",
                callback_data="describe_finish"
            )],
            [InlineKeyboardButton(
                text="🔙 В меню",
                callback_data="describe_back_to_menu"
            )]
        ]
    )