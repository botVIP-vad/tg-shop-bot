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
    get_all_offers,
    get_cart,
    get_offer,
    get_setting,
    remove_from_cart,
)
from handlers.helpers import (
    handle_bottom_menu_message,
    pop_nav,
    push_nav,
    reset_nav,
    transition,
)
from keyboards import (
    admin_offer_detail_kb,
    admin_offers_kb,
    admin_panel_kb,
    cancel_kb,
    cart_kb,
    contact_options_kb,
    main_menu_kb,
    offer_detail_kb,
    offers_list_kb,
)
from states import AddOffer, ContactAdmin, MakeOrder

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def format_cart_text(cart_items: list[dict]) -> str:
    lines = "\n".join(f"• {c['title']} — {c['price']}" for c in cart_items)
    return f"🛒 Ваша корзина:\n\n{lines}"


async def render_screen(screen_name: str, state: FSMContext, bot: Bot, chat_id: int, user_id: int):
    """Отрисовывает экран по его имени для навигации."""
    if screen_name == "main":
        await state.clear()
        busy_status = await get_setting("busy", "0")
        if busy_status == "1":
            status_line = "\n\n🟡 Сейчас немного загружены, ответим в ближайшее время."
        elif busy_status == "2":
            status_line = "\n\n🔴 Сейчас мы очень загружены, ответим чуть позже."
        else:
            status_line = "\n\n🟢 Сейчас принимаем новые заказы."
        await transition(
            state, bot, chat_id,
            bot.send_message(
                chat_id,
                "Привет! 👋\n\n"
                "Это бот для заказа сайтов. Нажми «🌐 Заказать сайт», чтобы посмотреть доступные предложения."
                + status_line,
                reply_markup=main_menu_kb(is_admin(user_id)),
            ),
        )

    elif screen_name == "offers":
        offers = await get_active_offers()
        if not offers:
            await transition(
                state, bot, chat_id,
                bot.send_message(chat_id, "Пока нет доступных предложений. Загляните позже 🙌", reply_markup=cancel_kb())
            )
        else:
            await transition(
                state, bot, chat_id,
                bot.send_message(chat_id, "Выберите предложение:", reply_markup=offers_list_kb(offers))
            )

    elif screen_name.startswith("offer_detail:"):
        offer_id = int(screen_name.split(":")[1])
        offer = await get_offer(offer_id)
        if not offer:
            await render_screen("offers", state, bot, chat_id, user_id)
            return

        caption = f"<b>{offer['title']}</b>\n\n{offer['description']}\n\n💰 Цена: {offer['price']}"
        if offer.get("photo_id"):
            send_coro = bot.send_photo(
                chat_id, photo=offer["photo_id"], caption=caption, reply_markup=offer_detail_kb(offer_id)
            )
        else:
            send_coro = bot.send_message(chat_id, caption, reply_markup=offer_detail_kb(offer_id))
        await transition(state, bot, chat_id, send_coro)

    elif screen_name == "cart":
        cart_items = await get_cart(user_id)
        if not cart_items:
            await transition(
                state, bot, chat_id,
                bot.send_message(chat_id, "🛒 Ваша корзина пуста. Загляните в каталог: «🌐 Заказать сайт».", reply_markup=cancel_kb())
            )
        else:
            await transition(
                state, bot, chat_id,
                bot.send_message(chat_id, format_cart_text(cart_items), reply_markup=cart_kb(cart_items))
            )

    elif screen_name == "order_contact":
        await state.set_state(MakeOrder.contact)
        await transition(
            state, bot, chat_id,
            bot.send_message(
                chat_id,
                "Отлично! Оставьте, пожалуйста, контакт для связи "
                "(номер телефона, @username или email):",
                reply_markup=cancel_kb(),
            ),
        )

    elif screen_name == "order_comment":
        await state.set_state(MakeOrder.comment)
        await transition(
            state, bot, chat_id,
            bot.send_message(
                chat_id,
                "Спасибо! Хотите добавить комментарий к заказу "
                "(пожелания, сроки и т.д.)? Если нет — напишите «-».",
                reply_markup=cancel_kb(),
            ),
        )

    elif screen_name == "contact_options":
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, "Как вам удобнее связаться?", reply_markup=contact_options_kb(ADMIN_USERNAME)),
        )

    elif screen_name == "contact_admin_msg":
        await state.set_state(ContactAdmin.message)
        await transition(
            state, bot, chat_id,
            bot.send_message(
                chat_id,
                "Напишите ваше сообщение одним текстом — мы получим его и ответим.",
                reply_markup=cancel_kb(),
            ),
        )
    elif screen_name == "rules":
        rules_text = (
            "<b>📜 Правила и условия работы</b>\n\n"
            "<b>1. 💳 Способы и порядок оплаты:</b>\n"
            "• <b>Принимаем:</b> СБП / Карты, Криптовалюта (USDT / TON / BTC), Telegram Stars ⭐️\n"
            "• 🎁 <b>Скидка 10%</b> при оплате в <b>криптовалюте</b>!\n"
            "• <b>Предоплата:</b> 30% от стоимости заказа перед началом разработки.\n"
            "• <b>Окончательный расчет:</b> оставшиеся 70% выплачиваются после полного завершения проекта и демонстрации результата.\n\n"
            "<b>2. 📋 Согласование ТЗ:</b>\n"
            "• Все требования и ключевые детали проекта фиксируются до старта работы.\n\n"
            "<b>3. 🛠 Правки и доработки:</b>\n"
            "• Бесплатные правки и корректировки в рамках утвержденного ТЗ.\n\n"
            "<b>4. 🔒 Гарантия и поддержка:</b>\n"
            "• <b>14 дней</b> бесплатной технической поддержки и устранения ошибок после передачи проекта.\n\n"
            "<b>5. 🤝 Прозрачность:</b>\n"
            "• Регулярная демонстрация промежуточных результатов в процессе разработки."
        )
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, rules_text, reply_markup=cancel_kb())
        )

    elif screen_name == "admin_panel":
        await state.clear()
        busy = (await get_setting("busy", "0")) == "1"
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, "⚙️ Админ-панель", reply_markup=admin_panel_kb(busy))
        )

    elif screen_name == "admin_offers":
        offers = await get_all_offers()
        if not offers:
            await transition(
                state, bot, chat_id,
                bot.send_message(chat_id, "Офферов пока нет.", reply_markup=cancel_kb())
            )
        else:
            await transition(
                state, bot, chat_id,
                bot.send_message(
                    chat_id,
                    "📋 Все офферы (🟢 активен / 🔴 скрыт):",
                    reply_markup=admin_offers_kb(offers),
                )
            )

    elif screen_name.startswith("admin_offer_detail:"):
        offer_id = int(screen_name.split(":")[1])
        offer = await get_offer(offer_id)
        if not offer:
            await render_screen("admin_offers", state, bot, chat_id, user_id)
            return

        caption = (
            f"<b>{offer['title']}</b>\n\n{offer['description']}\n\n"
            f"💰 {offer['price']}\nСтатус: {'🟢 активен' if offer['is_active'] else '🔴 скрыт'}"
        )
        if offer.get("photo_id"):
            send_coro = bot.send_photo(
                chat_id, photo=offer["photo_id"], caption=caption,
                reply_markup=admin_offer_detail_kb(offer_id, offer["is_active"]),
            )
        else:
            send_coro = bot.send_message(
                chat_id, caption, reply_markup=admin_offer_detail_kb(offer_id, offer["is_active"])
            )
        await transition(state, bot, chat_id, send_coro)

    elif screen_name == "add_offer_title":
        await state.set_state(AddOffer.title)
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, "Введите название оффера (например: «Лендинг под ключ»):", reply_markup=cancel_kb())
        )

    elif screen_name == "add_offer_description":
        await state.set_state(AddOffer.description)
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, "Введите описание оффера:", reply_markup=cancel_kb())
        )

    elif screen_name == "add_offer_price":
        await state.set_state(AddOffer.price)
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, "Укажите цену (например: «от 15 000 ₽»):", reply_markup=cancel_kb())
        )

    elif screen_name == "add_offer_photo":
        await state.set_state(AddOffer.photo)
        await transition(
            state, bot, chat_id,
            bot.send_message(chat_id, "Пришлите изображение для этого оффера (одним фото):", reply_markup=cancel_kb())
        )


@router.callback_query(F.data.in_({"nav_back", "cancel", "back_to_offers"}))
async def nav_back_handler(callback: CallbackQuery, state: FSMContext):
    prev_screen = await pop_nav(state)
    await render_screen(prev_screen, state, callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await render_screen("main", state, message.bot, message.chat.id, message.from_user.id)


@router.message(F.text == "🌐 Заказать сайт")
async def show_offers(message: Message, state: FSMContext):
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await push_nav(state, "offers")
    await render_screen("offers", state, message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data.startswith("offer:"))
async def show_offer_detail(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    screen_name = f"offer_detail:{offer_id}"
    await push_nav(state, screen_name)
    await render_screen(screen_name, state, callback.bot, callback.message.chat.id, callback.from_user.id)
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
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await push_nav(state, "cart")
    await render_screen("cart", state, message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data.startswith("cart_remove:"))
async def cart_remove(callback: CallbackQuery, state: FSMContext):
    offer_id = int(callback.data.split(":")[1])
    await remove_from_cart(callback.from_user.id, offer_id)
    await callback.answer("Убрано из корзины")
    await render_screen("cart", state, callback.bot, callback.message.chat.id, callback.from_user.id)


@router.callback_query(F.data == "cart_checkout")
async def cart_checkout(callback: CallbackQuery, state: FSMContext):
    cart_items = await get_cart(callback.from_user.id)
    if not cart_items:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    await state.update_data(offer_ids=[c["id"] for c in cart_items], from_cart=True)
    await push_nav(state, "order_contact")
    await render_screen("order_contact", state, callback.bot, callback.message.chat.id, callback.from_user.id)
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
    await push_nav(state, "order_contact")
    await render_screen("order_contact", state, callback.bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.message(MakeOrder.contact)
async def get_contact(message: Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await push_nav(state, "order_comment")
    await render_screen("order_comment", state, message.bot, message.chat.id, message.from_user.id)


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

    await reset_nav(state, "main")
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


# --- Связь с админом ---

@router.message(F.text == "💬 Написать нам")
async def contact_menu(message: Message, state: FSMContext):
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await push_nav(state, "contact_options")
    await render_screen("contact_options", state, message.bot, message.chat.id, message.from_user.id)


@router.callback_query(F.data == "contact_via_bot")
async def contact_via_bot(callback: CallbackQuery, state: FSMContext):
    await push_nav(state, "contact_admin_msg")
    await render_screen("contact_admin_msg", state, callback.bot, callback.message.chat.id, callback.from_user.id)
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

    await reset_nav(state, "main")
    await transition(
        state, message.bot, message.chat.id,
        message.answer(
            "✅ Сообщение отправлено! Мы ответим вам в ближайшее время.",
            reply_markup=main_menu_kb(is_admin(message.from_user.id)),
        ),
    )


@router.message(F.text == "📜 Условия работы")
async def show_rules(message: Message, state: FSMContext):
    await handle_bottom_menu_message(state, message.bot, message.chat.id, message.message_id)
    await reset_nav(state, "main")
    await push_nav(state, "rules")
    await render_screen("rules", state, message.bot, message.chat.id, message.from_user.id)




