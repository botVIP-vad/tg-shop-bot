import asyncio

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

# Небольшая пауза перед удалением — сглаживает переход между экранами
DELETE_DELAY = 0.4


async def safe_delete(message: Message):
    """Удаляет сообщение пользователя с небольшой задержкой (для более плавного перехода)."""
    try:
        await asyncio.sleep(DELETE_DELAY)
        await message.delete()
    except Exception:
        pass


async def transition(state: FSMContext, bot: Bot, chat_id: int, send_coro):
    """
    Отправляет новое сообщение бота и только ПОСЛЕ этого, с небольшой паузой,
    удаляет предыдущее отслеживаемое сообщение — переход выглядит менее резким,
    чем если сначала стереть старое, а потом показать новое.
    """
    data = await state.get_data()
    old_id = data.get("last_bot_msg_id")

    sent = await send_coro
    await state.update_data(last_bot_msg_id=sent.message_id)

    if old_id:
        try:
            await asyncio.sleep(DELETE_DELAY)
            await bot.delete_message(chat_id, old_id)
        except Exception:
            pass

    return sent


async def delete_tracked(state: FSMContext, bot: Bot, chat_id: int):
    """Удаляет предыдущее отслеживаемое сообщение бота в этом чате, если оно есть."""
    data = await state.get_data()
    old_id = data.get("last_bot_msg_id")
    if old_id:
        try:
            await bot.delete_message(chat_id, old_id)
        except Exception:
            pass


async def track(state: FSMContext, sent_message: Message):
    """Запоминает id только что отправленного сообщения бота, чтобы потом его удалить."""
    await state.update_data(last_bot_msg_id=sent_message.message_id)


# --- Навигация и отслеживание сообщений нижнего меню ---

async def handle_bottom_menu_message(state: FSMContext, bot: Bot, chat_id: int, user_msg_id: int):
    """
    Удаляет предыдущее сообщение пользователя, отправленное при выборе в нижнем меню,
    когда пользователь выбирает другой пункт в нижнем меню.
    """
    data = await state.get_data()
    old_menu_msg_id = data.get("last_user_menu_msg_id")
    if old_menu_msg_id and old_menu_msg_id != user_msg_id:
        try:
            await bot.delete_message(chat_id, old_menu_msg_id)
        except Exception:
            pass
    await state.update_data(last_user_menu_msg_id=user_msg_id)


async def push_nav(state: FSMContext, screen: str):
    """Добавляет экран в стек навигации."""
    data = await state.get_data()
    history = list(data.get("nav_history", []))
    if not history or history[-1] != screen:
        history.append(screen)
        await state.update_data(nav_history=history)


async def pop_nav(state: FSMContext) -> str:
    """Извлекает предыдущий экран из стека навигации."""
    data = await state.get_data()
    history = list(data.get("nav_history", []))
    if len(history) > 1:
        history.pop()  # Извлекаем текущий экран
        prev_screen = history[-1]
        await state.update_data(nav_history=history)
        return prev_screen
    elif len(history) == 1:
        history.pop()
        await state.update_data(nav_history=[])
        return "main"
    return "main"


async def reset_nav(state: FSMContext, start_screen: str = "main"):
    """Сбрасывает стек навигации и задает начальный экран."""
    await state.update_data(nav_history=[start_screen])
