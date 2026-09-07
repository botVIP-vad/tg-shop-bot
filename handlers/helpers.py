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
