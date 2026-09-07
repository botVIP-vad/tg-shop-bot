from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS
from database import add_offer, delete_offer, get_all_offers, get_offer, get_setting, set_setting, toggle_offer
from handlers.helpers import safe_delete, transition
from keyboards import (
    admin_offer_detail_kb,
    admin_offers_kb,
    admin_panel_kb,
    cancel_kb,
    main_menu_kb,
)
from states import AddOffer

router = Router()


def admin_only(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    busy = (await get_setting("busy", "0")) == "1"
    await transition(state, message.bot, message.chat.id,
                      message.answer("⚙️ Админ-панель", reply_markup=admin_panel_kb(busy)))
    await safe_delete(message)


@router.message(F.text == "⚙️ Админ-панель")
async def admin_panel_button(message: Message, state: FSMContext):
    if not admin_only(message.from_user.id):
        return
    busy = (await get_setting("busy", "0")) == "1"
    await transition(state, message.bot, message.chat.id,
                      message.answer("⚙️ Админ-панель", reply_markup=admin_panel_kb(busy)))
    await safe_delete(message)


@router.callback_query(F.data == "admin_toggle_busy")
async def admin_toggle_busy(callback: CallbackQuery):
    if not admin_only(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    current = await get_setting("busy", "0")
    new_val = "0" if current == "1" else "1"
    await set_setting("busy", new_val)
    await callback.answer("Статус обновлён")
    try:
        await callback.message.edit_reply_markup(reply_markup=admin_panel_kb(new_val == "1"))
    except Exception:
        pass


@router.callback_query(F.data == "admin_add_offer")
async def admin_add_offer_start(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    await state.set_state(AddOffer.title)
    await transition(
        state, callback.bot, callback.message.chat.id,
        callback.message.answer(
            "Введите название оффера (например: «Лендинг под ключ»):",
            reply_markup=cancel_kb(),
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await transition(
        state, callback.bot, callback.message.chat.id,
        callback.message.answer(
            "🏠 Главное меню",
            reply_markup=main_menu_kb(admin_only(callback.from_user.id)),
        ),
    )
    await callback.answer()


@router.message(AddOffer.title)
async def add_offer_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddOffer.description)
    await transition(state, message.bot, message.chat.id,
                      message.answer("Введите описание оффера:", reply_markup=cancel_kb()))
    await safe_delete(message)


@router.message(AddOffer.description)
async def add_offer_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddOffer.price)
    await transition(state, message.bot, message.chat.id,
                      message.answer("Укажите цену (например: «от 15 000 ₽»):", reply_markup=cancel_kb()))
    await safe_delete(message)


@router.message(AddOffer.price)
async def add_offer_price(message: Message, state: FSMContext):
    await state.update_data(price=message.text)
    await state.set_state(AddOffer.photo)
    await transition(state, message.bot, message.chat.id,
                      message.answer("Пришлите изображение для этого оффера (одним фото):", reply_markup=cancel_kb()))
    await safe_delete(message)


@router.message(AddOffer.photo, F.photo)
async def add_offer_photo(message: Message, state: FSMContext):
    data = await state.get_data()

    if not data.get("title") or not data.get("description") or not data.get("price"):
        await state.clear()
        await transition(
            state, message.bot, message.chat.id,
            message.answer(
                "⚠️ Данные о предыдущих шагах не сохранились (например, бот был перезапущен "
                "в процессе). Пожалуйста, начните добавление оффера заново: "
                "«⚙️ Админ-панель» → «➕ Добавить оффер».",
                reply_markup=main_menu_kb(True),
            ),
        )
        await safe_delete(message)
        return

    photo_id = message.photo[-1].file_id

    offer_id = await add_offer(
        title=data["title"],
        description=data["description"],
        price=data["price"],
        photo_id=photo_id,
    )

    await state.clear()
    await transition(
        state, message.bot, message.chat.id,
        message.answer_photo(
            photo=photo_id,
            caption=(
                f"✅ Оффер #{offer_id} создан!\n\n"
                f"<b>{data['title']}</b>\n{data['description']}\n💰 {data['price']}"
            ),
            reply_markup=main_menu_kb(True),
        ),
    )
    await safe_delete(message)


@router.message(AddOffer.photo)
async def add_offer_photo_invalid(message: Message, state: FSMContext):
    await transition(state, message.bot, message.chat.id,
                      message.answer("Пожалуйста, пришлите именно изображение (фото).", reply_markup=cancel_kb()))
    await safe_delete(message)


@router.callback_query(F.data == "admin_list_offers")
async def admin_list_offers(callback: CallbackQuery, state: FSMContext):
    if not admin_only(callback.from_user.id):
        await callback.answer("Недостаточно прав", show_alert=True)
        return
    offers = await get_all_offers()
    if not offers:
        await transition(state, callback.bot, callback.message.chat.id,
                          callback.message.answer("Офферов пока нет."))
        await callback.answer()
        return
    await transition(
        state, callback.bot, callback.message.chat.id,
        callback.message.answer(
            "📋 Все офферы (🟢 активен / 🔴 скрыт):",
            reply_markup=admin_offers_kb(offers),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_offer:"))
async def admin_offer_detail(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    offer = await get_offer(offer_id)
    if not offer:
        await callback.answer("Оффер не найден", show_alert=True)
        return

    caption = (
        f"<b>{offer['title']}</b>\n\n{offer['description']}\n\n"
        f"💰 {offer['price']}\nСтатус: {'🟢 активен' if offer['is_active'] else '🔴 скрыт'}"
    )

    if offer.get("photo_id"):
        send_coro = callback.message.answer_photo(
            photo=offer["photo_id"], caption=caption,
            reply_markup=admin_offer_detail_kb(offer_id, offer["is_active"]),
        )
    else:
        send_coro = callback.message.answer(
            caption, reply_markup=admin_offer_detail_kb(offer_id, offer["is_active"])
        )

    await transition(state, callback.bot, callback.message.chat.id, send_coro)
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
    offers = await get_all_offers()
    if offers:
        await transition(state, callback.bot, callback.message.chat.id,
                          callback.message.answer("📋 Все офферы:", reply_markup=admin_offers_kb(offers)))
    else:
        await transition(state, callback.bot, callback.message.chat.id,
                          callback.message.answer("Офферов больше нет."))
