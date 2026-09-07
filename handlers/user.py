from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import ADMIN_IDS, ADMIN_USERNAME
from database import (
    add_to_cart,
    clear_cart,
    create_order,
    get_active_offers,
    get_cart,
    get_offer,
    get_setting,
    remove_from_cart,
)
from handlers.helpers import safe_delete, transition
from keyboards import (
    cancel_kb,
    cart_kb,
    contact_options_kb,
    main_menu_kb,
    offer_detail_kb,
    offers_list_kb,
)
from states import ContactAdmin, MakeOrder

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def format_cart_text(cart_items: list[dict]) -> str:
    lines = "\n".join(f"• {c['title']} — {c['price']}" for c in cart_items)
    return f"🛒 Ваша корзина:\n\n{lines}"


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    busy = (await get_setting("busy", "0")) == "1"
    status_line = (
        "\n\n🔴 Сейчас мы очень загружены, ответим чуть позже."
        if busy
        else "\n\n🟢 Сейчас принимаем новые заказы."
    )

    await transition(
        state, message.bot, message.chat.id,
        message.answer(
            "Привет! 👋\n\n"
            "Это бот для заказа сайтов. Нажми «🌐 Заказать сайт», чтобы посмотреть доступные предложения."
            + status_line,
            reply_markup=main_menu_kb(is_admin(message.from_user.id)),
        ),
    )
    await safe_delete(message)


@router.message(F.text == "🌐 Заказать сайт")
async def show_offers(message: Message, state: FSMContext):
    offers = await get_active_offers()
    if not offers:
        await transition(state, message.bot, message.chat.id,
                          message.answer("Пока нет доступных предложений. Загляните позже 🙌"))
        await safe_delete(message)
        return
    await transition(state, message.bot, message.chat.id,
                      message.answer("Выберите предложение:", reply_markup=offers_list_kb(offers)))
    await safe_delete(message)


@router.callback_query(F.data == "back_to_offers")
async def back_to_offers(callback: CallbackQuery, state: FSMContext):
    offers = await get_active_offers()
    if not offers:
        await transition(state, callback.bot, callback.message.chat.id,
                          callback.message.answer("Пока нет доступных предложений."))
        await callback.answer()
        return
    await transition(state, callback.bot, callback.message.chat.id,
                      callback.message.answer("Выберите предложение:", reply_markup=offers_list_kb(offers)))
    await callback.answer()


@router.callback_query(F.data.startswith("offer:"))
async def show_offer_detail(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    offer = await get_offer(offer_id)
    if not offer:
        await callback.answer("Это предложение больше недоступно", show_alert=True)
        return

    caption = f"<b>{offer['title']}</b>\n\n{offer['description']}\n\n💰 Цена: {offer['price']}"

    if offer.get("photo_id"):
        send_coro = callback.message.answer_photo(
            photo=offer["photo_id"], caption=caption, reply_markup=offer_detail_kb(offer_id)
        )
    else:
        send_coro = callback.message.answer(caption, reply_markup=offer_detail_kb(offer_id))

    await transition(state, callback.bot, callback.message.chat.id, send_coro)
    await callback.answer()


# --- Корзина ---

@router.callback_query(F.data.startswith("cart_add:"))
async def cart_add(callback: CallbackQuery):
    offer_id = int(callback.data.split(":")[1])
    offer = await get_offer(offer_id)
    if not offer:
        await callback.answer("Этот оффер больше недоступен", show_alert=True)
        return
    await add_to_cart(callback.from_user.id, offer_id)
    await callback.answer("Добавлено в корзину ✅")


@router.message(F.text == "🛒 Корзина")
async def show_cart(message: Message, state: FSMContext):
    cart_items = await get_cart(message.from_user.id)
    if not cart_items:
        await transition(state, message.bot, message.chat.id,
                          message.answer("🛒 Ваша корзина пуста. Загляните в каталог: «🌐 Заказать сайт»."))
    else:
        await transition(state, message.bot, message.chat.id,
                          message.answer(format_cart_text(cart_items), reply_markup=cart_kb(cart_items)))
    await safe_delete(message)


@router.callback_query(F.data.startswith("cart_remove:"))
async def cart_remove(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    await remove_from_cart(callback.from_user.id, offer_id)
    await callback.answer("Убрано из корзины")

    cart_items = await get_cart(callback.from_user.id)
    if not cart_items:
        await transition(state, callback.bot, callback.message.chat.id,
                          callback.message.answer("🛒 Корзина пуста."))
    else:
        await transition(state, callback.bot, callback.message.chat.id,
                          callback.message.answer(format_cart_text(cart_items), reply_markup=cart_kb(cart_items)))


@router.callback_query(F.data == "cart_checkout")
async def cart_checkout(callback: CallbackQuery, state: FSMContext):
    cart_items = await get_cart(callback.from_user.id)
    if not cart_items:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    await state.update_data(offer_ids=[c["id"] for c in cart_items], from_cart=True)
    await state.set_state(MakeOrder.contact)
    await transition(
        state, callback.bot, callback.message.chat.id,
        callback.message.answer(
            "Оставьте, пожалуйста, контакт для связи по заказу из корзины "
            "(номер телефона, @username или email):",
            reply_markup=cancel_kb(),
        ),
    )
    await callback.answer()


# --- Оформление заказа (один оффер или корзина) ---

@router.callback_query(F.data.startswith("order:"))
async def start_order(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    offer = await get_offer(offer_id)
    if not offer:
        await callback.answer("Это предложение больше недоступно", show_alert=True)
        return

    await state.update_data(offer_ids=[offer_id], from_cart=False)
    await state.set_state(MakeOrder.contact)
    await transition(
        state, callback.bot, callback.message.chat.id,
        callback.message.answer(
            "Отлично! Оставьте, пожалуйста, контакт для связи "
            "(номер телефона, @username или email):",
            reply_markup=cancel_kb(),
        ),
    )
    await callback.answer()


@router.message(MakeOrder.contact)
async def get_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(MakeOrder.comment)
    await transition(
        state, message.bot, message.chat.id,
        message.answer(
            "Спасибо! Хотите добавить комментарий к заказу "
            "(пожелания, сроки и т.д.)? Если нет — напишите «-».",
            reply_markup=cancel_kb(),
        ),
    )
    await safe_delete(message)


@router.message(MakeOrder.comment)
async def get_comment(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    offer_ids = data.get("offer_ids", [])
    comment = "" if message.text == "-" else message.text

    order_ids = []
    titles = []
    for offer_id in offer_ids:
        offer = await get_offer(offer_id)
        if not offer:
            continue
        order_id = await create_order(
            user_id=message.from_user.id,
            username=message.from_user.username or "",
            full_name=message.from_user.full_name,
            offer_id=offer_id,
            contact=data["contact"],
            comment=comment,
        )
        order_ids.append(order_id)
        titles.append(offer["title"])

    if data.get("from_cart"):
        await clear_cart(message.from_user.id)

    await state.clear()
    await transition(
        state, message.bot, message.chat.id,
        message.answer(
            "✅ Заявка принята! Мы свяжемся с вами в ближайшее время.",
            reply_markup=main_menu_kb(is_admin(message.from_user.id)),
        ),
    )

    titles_text = "\n".join(f"- {t}" for t in titles) or "—"
    admin_text = (
        f"🆕 <b>Новая заявка</b> (номера: {', '.join('#' + str(i) for i in order_ids)})\n\n"
        f"Товары:\n{titles_text}\n\n"
        f"Клиент: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"Контакт: {data['contact']}\n"
        f"Комментарий: {comment or '—'}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            pass

    await safe_delete(message)


# --- Связь с админом ---

@router.message(F.text == "💬 Написать нам")
async def contact_menu(message: Message, state: FSMContext):
    await transition(
        state, message.bot, message.chat.id,
        message.answer("Как вам удобнее связаться?", reply_markup=contact_options_kb(ADMIN_USERNAME)),
    )
    await safe_delete(message)


@router.callback_query(F.data == "contact_via_bot")
async def contact_via_bot(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ContactAdmin.message)
    await transition(
        state, callback.bot, callback.message.chat.id,
        callback.message.answer(
            "Напишите ваше сообщение одним текстом — мы получим его и ответим.",
            reply_markup=cancel_kb(),
        ),
    )
    await callback.answer()


@router.message(ContactAdmin.message, F.text)
async def contact_receive(message: Message, state: FSMContext, bot: Bot):
    admin_text = (
        f"✉️ <b>Новое сообщение от пользователя</b>\n\n"
        f"От: {message.from_user.full_name} (@{message.from_user.username or '—'}, "
        f"id {message.from_user.id})\n\n"
        f"{message.text}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, admin_text)
        except Exception:
            pass

    await state.clear()
    await transition(
        state, message.bot, message.chat.id,
        message.answer(
            "✅ Сообщение отправлено! Мы ответим вам в ближайшее время.",
            reply_markup=main_menu_kb(is_admin(message.from_user.id)),
        ),
    )
    await safe_delete(message)


@router.message(F.text == "ℹ️ Мои заявки")
async def my_orders_stub(message: Message, state: FSMContext):
    await transition(
        state, message.bot, message.chat.id,
        message.answer(
            "Раздел «Мои заявки» можно расширить под ваши задачи — "
            "например, показывать статус заказа. Сейчас просто ждите обратной связи от менеджера 🙂"
        ),
    )
    await safe_delete(message)
