from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def main_menu_kb(is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardBuilder()
    kb.button(text="🌐 Заказать сайт")
    kb.button(text="🛒 Корзина")
    kb.button(text="💬 Написать нам")
    if is_admin:
        kb.button(text="⚙️ Админ-панель")
        kb.adjust(2, 2)
    else:
        kb.adjust(2, 1)
    return kb.as_markup(resize_keyboard=True)


def offers_list_kb(offers: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in offers:
        kb.button(text=f"{o['title']} — {o['price']}", callback_data=f"offer:{o['id']}")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def offer_detail_kb(offer_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Заказать этот сайт", callback_data=f"order:{offer_id}")
    kb.button(text="🛒 В корзину", callback_data=f"cart_add:{offer_id}")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def cart_kb(cart_items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in cart_items:
        kb.button(text=f"❌ Убрать: {item['title']}", callback_data=f"cart_remove:{item['id']}")
    if cart_items:
        kb.button(text="✅ Оформить заказ", callback_data="cart_checkout")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def contact_options_kb(admin_username: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✍️ Написать через бота", callback_data="contact_via_bot")
    kb.button(text="🔗 Написать в Telegram", url=f"https://t.me/{admin_username}")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def admin_panel_kb(busy: bool = False) -> InlineKeyboardMarkup:
def admin_panel_kb(busy_status: str = "0") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить оффер", callback_data="admin_add_offer")
    kb.button(text="📋 Список офферов", callback_data="admin_list_offers")
    status_text = "🔴 Занят — нажмите, чтобы освободиться" if busy else "🟢 Свободен — нажмите, чтобы отметить занятость"
    if busy_status == "1":
        status_text = "🟡 Немного занят — нажмите, чтобы изменить"
    elif busy_status == "2":
        status_text = "🔴 Занят — нажмите, чтобы изменить"
    else:
        status_text = "🟢 Свободен — нажмите, чтобы изменить"
    kb.button(text=status_text, callback_data="admin_toggle_busy")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def admin_offers_kb(offers: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for o in offers:
        status = "🟢" if o["is_active"] else "🔴"
        kb.button(text=f"{status} {o['title']}", callback_data=f"admin_offer:{o['id']}")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def admin_offer_detail_kb(offer_id: int, is_active: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    toggle_text = "🔴 Скрыть" if is_active else "🟢 Показать"
    kb.button(text=toggle_text, callback_data=f"admin_toggle:{offer_id}")
    kb.button(text="🗑 Удалить", callback_data=f"admin_delete:{offer_id}")
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    kb.adjust(1)
    return kb.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="nav_back")
    return kb.as_markup()
