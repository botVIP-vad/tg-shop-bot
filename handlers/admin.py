from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database import add_offer, delete_offer, get_offer, get_setting, set_setting, toggle_offer
from handlers.helpers import handle_bottom_menu_message, push_nav, reset_nav
from handlers.user import render_screen
from keyboards import (
    admin_offer_detail_kb,
    admin_panel_kb,
)
from states import AddOffer

router = Router()


def admin_only(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await push_nav(state, "admin_panel")
    await render_screen("admin_panel", state, message.bot, message.chat.id, message.from_user.id)


@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel_button(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await push_nav(state, "admin_panel")
    await render_screen("admin_panel", state, message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data == "admin_toggle_busy")
async def admin_toggle_busy(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    current = await get_setting("busy", "0")
    if current == "0":
        new_val = "1"
    elif current == "1":
        new_val = "2"
    else:
        new_val = "0"
    await set_setting("busy", new_val)
    await callback.answer("Статус обновлён")
    try:
        await callback.message.edit_reply_markup(reply_markup=admin_panel_kb(new_val))
    except Exception:
        pass


@router.callback_query(F.data == "admin_add_offer")
async def admin_add_offer_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await push_nav(state, "add_offer_title")
    await render_screen("add_offer_title", state, callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.message(AddOffer.title)
async def add_offer_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await push_nav(state, "add_offer_description")
    await render_screen("add_offer_description", state, message.bot, message.chat.id, message.from_user.id)


@router.message(AddOffer.description)
async def add_offer_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await push_nav(state, "add_offer_price")
    await render_screen("add_offer_price", state, message.bot, message.chat.id, message.from_user.id)


@router.message(AddOffer.price)
async def add_offer_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await push_nav(state, "add_offer_photo")
    await render_screen("add_offer_photo", state, message.bot, message.chat.id, message.from_user.id)


@router.message(AddOffer.photo, F.photo)
async def add_offer_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    if not data.get("title") or not data.get("description") or not data.get("price"):
        await reset_nav(state, "main")
        await render_screen("main", state, message.bot, message.chat.id, message.from_user.id)
        return

    photo_id = message.photo[-1].file_id

    offer_id = await add_offer(
        title=data["title"],
        description=data["description"],
        price=data["price"],
        photo_id=photo_id,
    )

    await reset_nav(state, "main")
    await render_screen("main", state, message.bot, message.chat.id, message.from_user.id)


@router.message(AddOffer.photo)
async def add_offer_photo_invalid(message: Message, state: FSMContext):
    await render_screen("add_offer_photo", state, message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data == "admin_list_offers")
async def admin_list_offers(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await push_nav(state, "admin_offers")
    await render_screen("admin_offers", state, callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_offer:"))
async def admin_offer_detail(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    screen_name = f"admin_offer_detail:{offer_id}"
    await push_nav(state, screen_name)
    await render_screen(screen_name, state, callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_toggle:"))
async def admin_toggle_offer(callback: CallbackQuery):
    offer_id = int(callback.data.split(":")[1])
    new_state = await toggle_offer(offer_id)
    if new_state is None:
        await callback.answer("Оффер не найден", show_alert=True)
        return
    await callback.answer("Статус обновлён")
    offer = await get_offer(offer_id)
    try:
        await callback.message.edit_reply_markup(
            reply_markup=admin_offer_detail_kb(offer_id, offer["is_active"])
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("admin_delete:"))
async def admin_delete_offer(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    await delete_offer(offer_id)
    await callback.answer("Оффер удалён")
    await render_screen("admin_offers", state, callback.bot, callback.message.chat.id, callback.from_user.id)
